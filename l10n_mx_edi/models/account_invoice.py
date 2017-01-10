# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.xml_utils import check_with_xsd
from odoo.tools.misc import file_open

import base64

from lxml import etree
from suds.client import Client
from itertools import groupby

from . import certificate


CFDI_TEMPLATE = 'l10n_mx_edi.cfdv32'
CFDI_XSD = 'l10n_mx_edi/data/%s/cfdv32.xsd'
CFDI_XSLT_CADENA = 'l10n_mx_edi/data/%s/cadenaoriginal_3_2.xslt'

#---------------------------------------------------------------------------
# Helpers
#---------------------------------------------------------------------------

def create_list_html(array):
    '''Convert an array of string to a html list
    '''
    if not array:
        return ''
    msg = ''
    for item in array:
        msg += '<li>' + item + '</li>'
    return '<ul>' + msg + '</ul>'

class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    l10n_mx_edi_pac_status = fields.Selection(
        selection=[
            ('retry', 'Retry'),
            ('to_sign', 'To sign'),
            ('signed', 'Signed'),
            ('to_cancel', 'To cancel'),
            ('cancelled', 'Cancelled')
        ],
        string='PAC status',
        help='Refers to the status of the invoice inside the PAC.',
        readonly=True,
        copy=False)
    l10n_mx_edi_sat_status = fields.Selection(
        selection=[
            ('undefined', 'Undefined'),
            ('not_available', 'Not available'),
            ('available', 'Available')
        ],
        string='SAT status',
        help='Refers to the status of the invoice inside the SAT system.',
        readonly=True,
        copy=False,
        required=True,
        default='undefined')
    l10n_mx_edi_cfdi_name = fields.Char(
        string='CFDI name',
        help='The attachment name of the CFDI.')
    l10n_mx_edi_partner_bank_id = fields.Many2one('res.partner.bank',
        string='Partner bank',
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('partner_id', '=', partner_id)]",
        help='The bank account the client will pay from. Leave empty if '
        'unkown and the XML will show "Unidentified".')
    l10n_mx_edi_payment_method_id = fields.Many2one(
        'l10n_mx_edi.payment.method',
        string='Payment Method',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Indicates the way the invoice was/will be paid, where the '
        'options could be: Cash, Nominal Check, Credit Card, etc. Leave empty '
        'if unkown and the XML will show "Unidentified".',
        default=lambda self: self.env.ref('l10n_mx_edi.payment_method_na',
                                          raise_if_not_found=False))
    l10n_mx_edi_uuid = fields.Char('Fiscal Folio', copy=False, index=True, readonly=True,
        help='Folio in electronic invoice, is returned by SAT when send to stamp.')

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        '''Set the payment bank account on the invoice as the first of the selected partner.
        '''
        res = super(AccountInvoice, self)._onchange_partner_id()
        if self.commercial_partner_id.bank_ids:
            self.l10n_mx_edi_partner_bank_id = self.commercial_partner_id.bank_ids[0].id
        return res

    #---------------------------------------------------------------------------
    # PAC related methods
    #---------------------------------------------------------------------------

    @api.model
    def l10n_mx_edi_get_service_client(self, service_type, company_id=None):
        '''Try to call the PAC as suds client. This method is usefull to handle several errors
        during the process. The returned values contains the client, the username, the password and
        the 'multi' boolean (in case we want to send several invoices by a single batch).
        :service_type: 'sign', 'cancel' or 'sat_inv'
        :company_id: the company_id containing the pac
        '''
        sat_flag = service_type == 'sat_inv'
        if sat_flag:
            infos = {'url': 'https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc?wsdl'}
        else:
            if not company_id:
                company_id = self.env.user.company_id
            pac_name = company_id.l10n_mx_edi_pac
            if not pac_name:
                return {'error': _('No PAC specified')}
            infos_func = '_l10n_mx_edi_%s_infos' % pac_name
            if not hasattr(self, infos_func):
                return {'error': _('Method %s not found') % infos_func}
            infos = getattr(self, infos_func)(company_id, service_type)
        url = infos.pop('url', None)
        username = infos.pop('username', None)
        password = infos.pop('password', None)
        multi = infos.pop('multi', False)
        error = infos.pop('error', None)
        if error:
            return {'error': error}
        try:
            client = Client(url, timeout=20)
            return {'client': client, 'username': username, 'password': password, 'multi': multi}
        except Exception as e:
            return {'error': _('Failed to call the suds client: %s' % str(e))}

    @api.model
    def l10n_mx_edi_get_service_response(self, service, params, client):
        '''Try to get the response from a suds client.
        :service - the service name to call
        :params - an array of parameters to call the service
        :client - an suds client

        The returned value is a dictionnary containing 'response' or 'error'.
        '''
        if not hasattr(client.service, service):
            return {'error': _('Service %s not found') % service}
        service_func = getattr(client.service, service)
        try:
            return {'response': service_func(*params)}
        except Exception as e:
            return {'error': _('Failed to process the response: %s' % str(e))}

    @api.multi
    def l10n_mx_edi_get_pac_version(self, pac_name):
        '''Returns the cfdi version of the pac but looking for a method named
        '_l10n_mx_edi_%s_version' % pac_name. By default, the version is 3.2.
        '''
        version_func = '_l10n_mx_edi_%s_version' % pac_name
        if not hasattr(self, version_func):
            return 3.2
        return getattr(self, version_func)()

    @api.multi
    def _l10n_mx_edi_get_cfdi_values(self):
        '''Create values that will be used as parameters to request the PAC sign/cancel services.
        These values may be the 'uuid', 'supplier_rfc', 'customer_rfc', 'total', 'certificate_id', 'cfdi' 
        '''
        self.ensure_one()
        values = {}
        domain = [
            ('res_id','=', self.id),
            ('res_model', '=', self._name),
            ('name', '=', self.l10n_mx_edi_cfdi_name)]
        attachment_id = self.env['ir.attachment'].search(domain, limit=1)
        if attachment_id:
            xml = base64.decodestring(attachment_id.datas)
            tree = etree.fromstring(xml)
            node_sup = tree.find('.//{http://www.sat.gob.mx/cfd/3}Emisor')
            node_cus = tree.find('.//{http://www.sat.gob.mx/cfd/3}Receptor')
            node_uuid = tree.find('.//{http://www.sat.gob.mx/TimbreFiscalDigital}TimbreFiscalDigital')
            if node_uuid is not None:
                values['uuid'] = node_uuid.attrib['UUID']
            values['supplier_rfc'] = node_sup.attrib['rfc']
            values['customer_rfc'] = node_cus.attrib['rfc']
            values['total'] = tree.attrib['total']
            cer_domain = [('serial_number', '=', tree.attrib['noCertificado'])]
            values['certificate_id'] = self.env['l10n_mx_edi.certificate'].sudo().search(cer_domain, limit=1)
            xml = etree.tostring(tree)
            values['cfdi'] = base64.encodestring(xml)
        return values

    @api.multi
    def _l10n_mx_edi_call_service(self, service_type):
        '''Generic method that contains the logic to call and process a service from the PACs.
        '''
        error_msg = _('Errors while requesting the PAC')
        # Regroup the invoices by company (= by pac)
        comp_x_records = groupby(self, lambda r: r.company_id)
        for company, records in comp_x_records:
            pac_name = company.l10n_mx_edi_pac
            if not pac_name:
                continue
            service_func = '_l10n_mx_edi_%s_%s' % (pac_name, service_type)
            # Check if a method is found for this pair service/pac
            if not hasattr(self, service_func):
                for record in records:
                    record.message_post(
                        body=error_msg + create_list_html([_('Methods %s not found') % service_func]),
                        subtype='account.mt_invoice_validated')
                continue
            # Create the client
            client_values = self.l10n_mx_edi_get_service_client(service_type, company)
            error = client_values.pop('error', None)
            if error:
                for record in records:
                    record.message_post(
                        body=error_msg + create_list_html([error]),
                        subtype='account.mt_invoice_validated')
                continue
            client = client_values['client']
            multi = client_values['multi']
            username = client_values['username']
            password = client_values['password']
            # If multi is set to true, the method is called with the whole subset.
            # else, we process the service for each record
            if multi:
                getattr(records, service_func)(username, password, client)
            else:
                for record in records:
                    getattr(record, service_func)(username, password, client)

    @api.multi
    def _l10n_mx_edi_post_sign_process(self, xml_signed, code, msg):
        '''Post process the results of the sign service.
        :xml_signed: the xml signed datas codified in base64
        :code: an eventual error code
        :msg: an eventual error msg
        '''
        self.ensure_one()
        if xml_signed:
            # Update the content of the attachment
            domain = [
                ('res_id','=', self.id),
                ('res_model', '=', self._name),
                ('name', '=', self.l10n_mx_edi_cfdi_name)]
            attachment_id = self.env['ir.attachment'].search(domain, limit=1)
            attachment_id.write({
                'datas': xml_signed,
                'mimetype': 'application/xml'
            })
            # Store the uuid on the invoice
            tree = etree.fromstring(base64.decodestring(xml_signed))
            node_uuid = tree.find('.//{http://www.sat.gob.mx/TimbreFiscalDigital}TimbreFiscalDigital')
            self.l10n_mx_edi_uuid = node_uuid.attrib['UUID']
            # Update the pac status
            self.l10n_mx_edi_pac_status = 'signed'
            msg = create_list_html([_('The content of the attachment has been updated')])
            self.message_post(body=_('The sign service has been called with success') + msg,
                subtype='account.mt_invoice_validated')
        else:
            if msg:
                if code:
                    code = int(code)
                    msg = _('Code %d: %s') % (code, msg)
                msg = create_list_html([msg])
            else:
                msg = ''
            self.message_post(body=_('The sign service requested failed') + msg,
                subtype='account.mt_invoice_validated')

    @api.multi
    def _l10n_mx_edi_sign(self):
        '''Call the sign service with records that can be signed.
        '''
        records = self.search([
            ('l10n_mx_edi_pac_status', 'not in', ['signed', 'to_cancel', 'cancelled', 'retry']),
            ('id', 'in', self.ids)])
        records._l10n_mx_edi_call_service('sign')

    @api.multi
    def _l10n_mx_edi_post_cancel_process(self, cancelled, code, msg):
        '''Post process the results of the cancel service.
        :cancelled: is the cancel has been done with success
        :code: an eventual error code
        :msg: an eventual error msg
        '''
        self.ensure_one()
        if cancelled:
            self.l10n_mx_edi_pac_status = 'cancelled'
            self.message_post(body=_('The cancel service has been called with success'),
                subtype='account.mt_invoice_validated')
        else:
            if msg:
                if code:
                    code = int(code)
                    msg = _('Code %d: %s') % (code, msg)
                msg = create_list_html([msg])
            else:
                msg = ''
            self.message_post(body=_('The cancel service requested failed') + msg,
                subtype='account.mt_invoice_validated')

    @api.multi
    def _l10n_mx_edi_cancel(self):
        '''Call the cancel service with records that can be signed.
        '''
        records = self.search([
            ('l10n_mx_edi_pac_status', 'in', ['to_sign', 'signed', 'to_cancel', 'retry']),
            ('id', 'in', self.ids)])
        for record in records:
            if record.l10n_mx_edi_pac_status in ['to_sign', 'retry']:
                record.l10n_mx_edi_pac_status = 'cancelled'
                record.message_post(body=_('The cancel service has been called with success') % 'cancel', 
                    subtype='account.mt_invoice_validated')
            else:
                record.l10n_mx_edi_pac_status = 'to_cancel'
        records = self.search([
            ('l10n_mx_edi_pac_status', '=', 'to_cancel'),
            ('id', 'in', self.ids)])
        records._l10n_mx_edi_call_service('cancel')

    #---------------------------------------------------------------------------
    # PAC service methods
    #---------------------------------------------------------------------------

    @api.model
    def _l10n_mx_edi_solfact_infos(self, company_id, service_type):
        '''Request the informations related to the PAC in order to call its services.
        The service type can be 'sign' or 'cancel' and is required to return the right url.
        '''
        test = company_id.l10n_mx_edi_pac_test_env
        username = company_id.l10n_mx_edi_pac_username
        password = company_id.l10n_mx_edi_pac_password
        url = 'https://testing.solucionfactible.com/ws/services/Timbrado?wsdl'\
            if test else 'https://solucionfactible.com/ws/services/Timbrado?wsdl'
        return {
            'url': url,
            'multi': False,  # TODO: implement multi
            'username': 'testing@solucionfactible.com' if test else username,
            'password': 'timbrado.SF.16672' if test else password,
        }

    @api.multi
    def _l10n_mx_edi_solfact_sign(self, username, password, client):
        '''SIGN for Solucion Factible.
        '''
        # TODO: Do it on multi
        self.ensure_one()
        service = 'timbrar'
        values = self._l10n_mx_edi_get_cfdi_values()
        params = [username, password, values['cfdi'], False]
        response_values = self.l10n_mx_edi_get_service_response(service, params, client)
        error = response_values.pop('error', None)
        response = response_values.pop('response', None)
        if error:
            self.message_post(
                body=_('The sign service requested failed') + create_list_html([error]),
                subtype='account.mt_invoice_validated')
            return
        code = getattr(response.resultados[0], 'status', None)
        msg = getattr(response.resultados[0], 'mensaje', None)
        xml_signed = getattr(response.resultados[0], 'cfdiTimbrado', None)
        self._l10n_mx_edi_post_sign_process(xml_signed, code, msg)

    @api.multi
    def _l10n_mx_edi_solfact_cancel(self, username, password, client):
        '''CANCEL for Solucion Factible.
        '''
        # TODO: Do it on multi
        self.ensure_one()
        service = 'cancelar'
        values = self._l10n_mx_edi_get_cfdi_values()
        uuids = [values['uuid']]
        certificate_id = values['certificate_id']
        cer_pem = base64.encodestring(certificate.convert_cer_to_pem(base64.decodestring(certificate_id.content)))
        key_pem = base64.encodestring(certificate.convert_key_cer_to_pem(base64.decodestring(certificate_id.key), certificate_id.password))
        params = [username, password, uuids, cer_pem, key_pem, certificate_id.password]
        response_values = self.l10n_mx_edi_get_service_response(service, params, client)
        error = response_values.pop('error', None)
        response = response_values.pop('response', None)
        if error:
            self.message_post(
                body=_('The cancel service requested failed') + create_list_html([error]),
                subtype='account.mt_invoice_validated')
            return
        code = getattr(response.resultados[0], 'statusUUID', None)
        msg = getattr(response.resultados[0], 'mensaje', None)
        cancelled = code == '201' or code == '202'
        self._l10n_mx_edi_post_cancel_process(cancelled, code, msg)

    @api.multi
    def _l10n_mx_edi_finkok_infos(self, company_id, service_type):
        test = company_id.l10n_mx_edi_pac_test_env
        username = company_id.l10n_mx_edi_pac_username
        password = company_id.l10n_mx_edi_pac_password
        if service_type == 'sign':
            url = 'http://demo-facturacion.finkok.com/servicios/soap/stamp.wsdl'\
                if test else 'http://facturacion.finkok.com/servicios/soap/stamp.wsdl'
        else:
            url = 'http://demo-facturacion.finkok.com/servicios/soap/cancel.wsdl'\
                if test else 'http://facturacion.finkok.com/servicios/soap/cancel.wsdl'
        return {
            'url': url,
            'multi': False,  # TODO: implement multi
            'username': 'cfdi@vauxoo.com' if test else username,
            'password': 'vAux00__' if test else password,
        }

    @api.multi
    def _l10n_mx_edi_finkok_sign(self, username, password, client):
        '''SIGN for Finkok.
        '''
        # TODO: Do it on multi
        self.ensure_one()
        service = 'stamp'
        values = self._l10n_mx_edi_get_cfdi_values()
        params = [[values['cfdi']], username, password]
        response_values = self.l10n_mx_edi_get_service_response(service, params, client)
        error = response_values.pop('error', None)
        response = response_values.pop('response', None)
        if error:
            self.message_post(
                body=_('The cancel service requested failed') + create_list_html([error]),
                subtype='account.mt_invoice_validated')
            return
        msg = ''
        code = 0
        if response.Incidencias:
            code = getattr(response.Incidencias[0][0], 'CodigoError', None)
            msg = getattr(response.Incidencias[0][0], 'MensajeIncidencia', None)
        xml_signed = getattr(response, 'xml', None)
        if xml_signed:
            xml_signed = xml_signed.encode('utf-8').encode('base64')
        self._l10n_mx_edi_post_sign_process(xml_signed, code, msg)

    @api.multi
    def _l10n_mx_edi_finkok_cancel(self, username, password, client):
        '''CANCEL for Finkok.
        '''
        # TODO: Do it on multi
        self.ensure_one()
        service = 'cancel'
        values = self._l10n_mx_edi_get_cfdi_values()
        invoices_list = client.factory.create("UUIDS")
        invoices_list.uuids.string = [values['uuid']]
        company_id = self.company_id
        certificate_id = values['certificate_id']
        cer_pem = base64.encodestring(certificate.convert_cer_to_pem(base64.decodestring(certificate_id.content)))
        key_pem = base64.encodestring(certificate.convert_key_cer_to_pem(base64.decodestring(certificate_id.key), certificate_id.password))
        params = [invoices_list, username, password, company_id.vat, cer_pem, key_pem]
        response_values = self.l10n_mx_edi_get_service_response(service, params, client)
        error = response_values.pop('error', None)
        response = response_values.pop('response', None)
        if error:
            self.message_post(
                body=_('The cancel service requested failed') + create_list_html([error]),
                subtype='account.mt_invoice_validated')
            return
        if not hasattr(response, 'Folios'):
            error = _('A delay of 2 hours has to be respected before to cancel')
            self.message_post(
                body=_('The cancel service requested failed') + create_list_html([error]),
                subtype='account.mt_invoice_validated')
            return
        code = getattr(response.Folios[0][0], 'EstatusUUID', None)
        cancelled = code == '201' or code == '202'  # cancelled or previously cancelled
        msg = code != 201 and code != 202 and "Cancelling get an error"
        self._l10n_mx_edi_post_cancel_process(cancelled, code, msg)

    #---------------------------------------------------------------------------
    # Account invoice methods
    #---------------------------------------------------------------------------

    @api.multi
    def _l10n_mx_edi_create_taxes_cfdi_values(self):
        self.ensure_one()
        values = {
            'total_withhold': 0,
            'total_transferred': 0,
            'withholding': [],
            'transferred': [],
        }
        for tax in self.tax_line_ids:
            tax_dict = {
                'name': (tax.tax_id.description or tax.tax_id.name).upper(),
                'amount': round(abs(tax.amount or 0.0), 2),
                'rate': round(abs(tax.tax_id.amount), 2),
            }
            if tax.amount >= 0:
                values['total_transferred'] += abs(tax.amount or 0.0)
                values['transferred'].append(tax_dict)
            else:
                values['total_withhold'] += abs(tax.amount or 0.0)
                values['withholding'].append(tax_dict)
        return values

    @api.multi
    def _l10n_mx_edi_create_cfdi_values(self):
        '''Create the values to fill the CFDI template.
        '''
        self.ensure_one()
        precision_digits = self.env['decimal.precision'].precision_get('Account')
        values = {
            'record': self,
            'currency_name': self.currency_id.name,
            'supplier': self.company_id.partner_id.commercial_partner_id,
            'issued': self.journal_id.l10n_mx_address_issued_id,
            'customer': self.partner_id.commercial_partner_id,
            'number': self.number,
            'fiscal_position': self.company_id.partner_id.property_account_position_id.name,
            'payment_method': self.l10n_mx_edi_payment_method_id.name,

            'amount_total': '%0.*f' % (precision_digits, self.amount_total),
            'amount_untaxed': '%0.*f' % (precision_digits, self.amount_untaxed),
        }

        values['document_type'] = 'ingreso' if self.type == 'out_invoice' else 'egreso'

        if len(self.payment_term_id.line_ids) > 1:
            values['payment_policy'] = 'Pago en parcialidades'
        else:
            values['payment_policy'] = 'Pago en una sola exhibicion'

        values['domicile'] = '%s %s, %s' % (
                self.company_id.city,
                self.company_id.state_id.name,
                self.company_id.country_id.name
            )

        values['rfc'] = lambda p: p.vat[2:].replace(' ', '')
        values['subtotal_wo_discount'] = lambda l: l.quantity * l.price_unit

        values['taxes'] = self._l10n_mx_edi_create_taxes_cfdi_values()

        if self.l10n_mx_edi_partner_bank_id:
            digits = [s for s in self.l10n_mx_edi_partner_bank_id.acc_number if s.isdigit()]
            acc_4number = ''.join(digits)[-4:]
            values['account_4num'] = acc_4number if len(acc_4number) == 4 else None
        else:
            values['account_4num'] = None

        return values

    @api.multi
    def _l10n_mx_edi_create_cfdi(self):
        '''Creates and returns a dictionnary containing 'cfdi' if the cfdi is well created, 'error' otherwise.
        '''
        self.ensure_one()
        qweb = self.env['ir.qweb']
        error_log = []
        company_id = self.company_id
        pac_name = company_id.l10n_mx_edi_pac
        values = self._l10n_mx_edi_create_cfdi_values()

        # -----------------------
        # Check the configuration
        # -----------------------
        # -Check certificate
        certificate_ids = company_id.l10n_mx_edi_certificate_ids
        certificate_id = certificate_ids.sudo().get_valid_certificate()
        if not certificate_id:
            error_log.append(_('No valid certificate found'))

        # -Check PAC
        if pac_name:
            pac_test_env = company_id.l10n_mx_edi_pac_test_env
            pac_username = company_id.l10n_mx_edi_pac_username
            pac_password = company_id.l10n_mx_edi_pac_password
            if not pac_test_env and not (pac_username and pac_password):
                error_log.append(_('No PAC credentials specified.'))
        else:
            error_log.append(_('No PAC specified.'))

        if error_log:
            return {'error': _('Please check your configuration: ') + create_list_html(error_log)}

        # -----------------------
        # Create the EDI document
        # -----------------------
        version = self.l10n_mx_edi_get_pac_version(pac_name)
        parser = etree.XMLParser(remove_blank_text=True)

        # -Compute certificate data
        values['date'] = certificate_id.sudo().get_mx_current_datetime().strftime('%Y-%m-%dT%H:%M:%S')
        values['certificate_number'] = certificate_id.serial_number
        values['certificate'] = certificate_id.sudo().get_data()[0]

        # -Compute cfdi
        cfdi = qweb.render(CFDI_TEMPLATE, values=values)
        # TEMP QWEB FIX
        cfdi = cfdi.replace('{http://www.w3.org/2001/XMLSchema-instance}', 'xsi:')

        # -Compute cadena
        tree = etree.fromstring(cfdi, parser=parser)
        xslt_root = etree.parse(file_open(CFDI_XSLT_CADENA % version))
        cadena = str(etree.XSLT(xslt_root)(tree))

        # Post append cadena
        tree.attrib['sello'] = certificate_id.sudo().get_encrypted_cadena(cadena)

        # Check with xsd
        try:
            error_log = check_with_xsd(tree, CFDI_XSD % version)
        except Exception as e:
            return {'error': _('The cfdi generated is not valid') + create_list_html(e.name.split('\n'))}

        # Post append addenda
        if self.partner_id.l10n_mx_edi_addenda:
            cfdi_addenda_node = tree.find(".//{http://www.sat.gob.mx/cfd/3}Addenda")
            addenda_tree = etree.fromstring(self.partner_id.l10n_mx_edi_addenda.arch, parser=parser)
            addenda_str = qweb.render(addenda_tree, values=values)
            addenda_node = etree.fromstring(addenda_str, parser=parser)
            cfdi_addenda_node.extend(addenda_node)

        return {'cfdi': etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')}

    @api.multi
    def _l10n_mx_edi_retry(self):
        '''Try to generate the cfdi attachment and then, sign it.
        '''
        for record in self:
            cfdi_values = record._l10n_mx_edi_create_cfdi()
            error = cfdi_values.pop('error', None)
            cfdi = cfdi_values.pop('cfdi', None)
            if error:
                # cfdi failed to be generated
                record.l10n_mx_edi_pac_status = 'retry'
                record.message_post(body=error, subtype='account.mt_invoice_validated')
            else:
                # cfdi has been successfully generated
                record.l10n_mx_edi_pac_status = 'to_sign'
                filename = record.l10n_mx_edi_cfdi_name
                attachment_id = self.env['ir.attachment'].create({
                    'name': filename,
                    'res_id': record.id,
                    'res_model': unicode(record._name),
                    'datas': base64.encodestring(cfdi),
                    'datas_fname': filename,
                    'type': 'binary',
                    'description': 'Mexican invoice',
                    })
                record.message_post(
                    body=_('CFDI document generated (may be not signed)'),
                    attachment_ids=[attachment_id.id],
                    subtype='account.mt_invoice_validated')
                record._l10n_mx_edi_sign()

    @api.multi
    def invoice_validate(self):
        '''Generates the cfdi attachments for mexican companies when validated.'''
        result = super(AccountInvoice, self).invoice_validate()
        for record in self:
            if record.company_id.country_id == self.env.ref('base.mx'):
                record.l10n_mx_edi_cfdi_name = ('%s-MX-Invoice-2.1.xml' % self.number).replace('/', '')
                record._l10n_mx_edi_retry()
        return result

    @api.multi
    def action_invoice_cancel(self):
        '''Cancel the cfdi attachments for mexican companies when cancelled.'''
        result = super(AccountInvoice, self).action_invoice_cancel()
        for record in self:
            if record.company_id.country_id == self.env.ref('base.mx'):
                record._l10n_mx_edi_cancel()
        return result

    @api.multi
    def l10n_mx_edi_update_pac_status(self):
        '''Synchronize both systems: Odoo & PAC if the invoices need to be signed or cancelled.
        '''
        for record in self:
            if record.l10n_mx_edi_pac_status == 'to_sign':
                record._l10n_mx_edi_sign()
            elif record.l10n_mx_edi_pac_status == 'to_cancel':
                record._l10n_mx_edi_cancel()
            elif record.l10n_mx_edi_pac_status == 'retry':
                record._l10n_mx_edi_retry()

    @api.multi
    def l10n_mx_edi_update_sat_status(self):
        '''Synchronize both systems: Odoo & SAT to make sure the invoice is valid.
        '''
        client_values = self.l10n_mx_edi_get_service_client('sat_inv')
        error = client_values.pop('error', None)
        if error:
            error_msg = _('Errors while requesting the SAT')
            for record in self:
                record.message_post(
                    body=error_msg + create_list_html([error]),
                    subtype='account.mt_invoice_validated')
            return
        client = client_values['client']
        error_resp = _('The SAT service failed to be requested')
        error_msg = _('The SAT service has responded: %s')
        for record in self:
            if (record.company_id.country_id == self.env.ref('base.mx') and record.l10n_mx_edi_pac_status == 'signed' and
            not record.l10n_mx_edi_sat_status == 'available'):
                values = record._l10n_mx_edi_get_cfdi_values()
                arg = '"?re=%s&rr=%s&tt=%s&id=%s' % (
                    values['supplier_rfc'], values['customer_rfc'], values['total'], values['uuid'])
                response_values = record.l10n_mx_edi_get_service_response('Consulta', [arg], client)
                error = response_values.pop('error', None)
                response = response_values.pop('response', None)
                if error:
                    record.message_post(
                        body=error_resp + create_list_html([error]),
                        subtype='account.mt_invoice_validated')
                    continue
                msg = response.CodigoEstatus
                #TODO get availability from response
                available = False
                if available:
                    record.l10n_mx_edi_sat_status = 'available'
                else:
                    record.l10n_mx_edi_sat_status = 'not_available'
                    record.message_post(
                        body=error_msg % msg,
                        subtype='account.mt_invoice_validated')
