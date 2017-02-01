# -*- coding: utf-8 -*-

import base64
from itertools import groupby

from lxml import etree
from lxml.objectify import fromstring
from suds.client import Client
from werkzeug import url_encode

from odoo import _, api, fields, models, tools
from odoo.tools.xml_utils import check_with_xsd

CFDI_TEMPLATE = 'l10n_mx_edi.cfdv32'
CFDI_XSD = 'l10n_mx_edi/data/%s/cfdv32.xsd'
CFDI_XSLT_CADENA = 'l10n_mx_edi/data/%s/cadenaoriginal_3_2.xslt'
# Mapped from original SAT state to l10n_mx_edi_sat_status selection value
# https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc?wsdl
CFDI_SAT_QR_STATE = {
    'No Encontrado': 'not_found',
    'Cancelado': 'cancelled',
    'Vigente': 'valid',
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_list_html(array):
    '''Convert an array of string to a html list.
    :param array: A list of strings
    :return: an empty string if not array, an html list otherwise.
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
            ('none', 'State not defined'),
            ('undefined', 'Not Synced Yet'),
            ('not_found', 'Not Found'),
            ('cancelled', 'Cancelled'),
            ('valid', 'Valid'),
        ],
        string='SAT status',
        help='Refers to the status of the invoice inside the SAT system.',
        readonly=True,
        copy=False,
        required=True,
        track_visibility='onchange',
        default='undefined')
    l10n_mx_edi_cfdi_name = fields.Char(string='CFDI name', copy=False, readonly=True,
        help='The attachment name of the CFDI.')
    l10n_mx_edi_partner_bank_id = fields.Many2one('res.partner.bank',
        string='Partner bank',
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('partner_id', '=', partner_id)]",
        help='The bank account the client will pay from. Leave empty if '
        'unkown and the XML will show "Unidentified".')
    l10n_mx_edi_payment_method_id = fields.Many2one('l10n_mx_edi.payment.method',
        string='Payment Method',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Indicates the way the invoice was/will be paid, where the '
        'options could be: Cash, Nominal Check, Credit Card, etc. Leave empty '
        'if unkown and the XML will show "Unidentified".',
        default=lambda self: self.env.ref('l10n_mx_edi.payment_method_na',
                                          raise_if_not_found=False))
    l10n_mx_edi_uuid = fields.Char('Fiscal Folio', copy=False, readonly=True,
        help='Unused field to remove in master')
    l10n_mx_edi_cfdi_uuid = fields.Char(string='Fiscal Folio', copy=False, readonly=True,
        help='Folio in electronic invoice, is returned by SAT when send to stamp.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi = fields.Binary(string='Cfdi content', copy=False, readonly=True,
        help='The cfdi xml content encoded in base64.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi_supplier_rfc = fields.Char(string='Supplier RFC', copy=False, readonly=True,
        help='The supplier tax identification number.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi_customer_rfc = fields.Char(string='Customer RFC', copy=False, readonly=True,
        help='The customer tax identification number.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi_amount = fields.Monetary(string='Total Amount', copy=False, readonly=True,
        help='The total amount reported on the cfdi.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi_certificate_id = fields.Many2one('l10n_mx_edi.certificate',
        string='Certificate', copy=False, readonly=True,
        help='The certificate used during the generation of the cfdi.',
        compute='_compute_cfdi_values')

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def l10n_mx_edi_get_customer_rfc(self):
        '''In Mexico depending of some cases the vat (rfc) is not mandatory to be recorded in customers, only for those
        cases instead try to force the record values and make documentation, given a customer the system will propose
        properly a vat (rfc) in order to generate properly the xml following this law:

        http://www.sat.gob.mx/informacion_fiscal/factura_electronica/Documents/cfdi/PyRFactElect.pdf.

        :return: XEXX010101000, XAXX010101000 or the customer vat depending of the country
        '''
        self.ensure_one()
        partner_id = self.partner_id.commercial_partner_id
        if partner_id.country_id and partner_id.country_id != self.env.ref('base.mx'):
            # Following Question 5 in legal Document.
            return 'XEXX010101000'
        if (partner_id.country_id == self.env.ref('base.mx') or not partner_id.country_id) and not partner_id.vat:
            self.message_post(
                body=_('Using General Public VAT because no vat found'),
                subtype='account.mt_invoice_validated')
            # Following Question 4 in legal Document.
            return 'XAXX010101000'
        # otherwise it returns what customer says and if False xml validation will be solving other cases.
        return partner_id.vat

    @api.model
    def l10n_mx_edi_retrieve_attachments(self):
        '''Retrieve all the cfdi attachments generated for this invoice.

        :return: An ir.attachment recordset
        '''
        self.ensure_one()
        if not self.l10n_mx_edi_cfdi_name:
            return []
        domain = [
            ('res_id', '=', self.id),
            ('res_model', '=', self._name),
            ('name', '=', self.l10n_mx_edi_cfdi_name)]
        return self.env['ir.attachment'].search(domain)

    @api.model
    def l10n_mx_edi_retrieve_last_attachment(self):
        attachment_ids = self.l10n_mx_edi_retrieve_attachments()
        return attachment_ids and attachment_ids[-1] or None

    @api.model
    def l10n_mx_edi_get_xml_etree(self, cfdi=None):
        '''Get an objectified tree representing the cfdi.
        If the cfdi is not specified, retrieve it from the attachment.

        :param cfdi: The cfdi as string
        :return: An objectified tree
        '''
        #TODO helper which is not of too much help and should be removed
        self.ensure_one()
        if cfdi is None:
            cfdi = base64.decodestring(self.l10n_mx_edi_cfdi)
        return fromstring(cfdi)

    @api.model
    def l10n_mx_edi_get_tfd_etree(self, cfdi):
        '''Get the TimbreFiscalDigital node from the cfdi.

        :param cfdi: The cfdi as etree
        :return: the TimbreFiscalDigital node
        '''
        self.ensure_one()
        if not hasattr(cfdi, 'Complemento'):
            return None
        attribute = 'tfd:TimbreFiscalDigital[1]'
        namespace = {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'}
        node = cfdi.Complemento.xpath(attribute, namespaces=namespace)
        return node[0] if node else False

    @api.model
    def l10n_mx_edi_generate_cadena(self, xslt_path, cfdi_as_tree):
        '''Generate the cadena of the cfdi based on an xslt file.
        The cadena is the sequence of data formed with the information contained within the cfdi.
        This can be encoded with the certificate to create the digital seal.
        Since the cadena is generated with the invoice data, any change in it will be noticed resulting in a different
        cadena and so, ensure the invoice has not been modified.

        :param xslt_path: The path to the xslt file.
        :param cfdi_as_tree: The cfdi converted as a tree
        :return: A string computed with the invoice data called the cadena
        '''
        self.ensure_one()
        xslt_root = etree.parse(tools.file_open(xslt_path))
        return str(etree.XSLT(xslt_root)(cfdi_as_tree))

    @api.model
    def l10n_mx_edi_is_customer_address_required(self):
        '''Look in the customer address to know if enough address information can be found to justify the creation
         of an address block in the xml.

        :return: True if at least one required field is found.
        '''
        self.ensure_one()
        partner_id = self.partner_id.commercial_partner_id
        address_fields = ['street_name',
                          'street_number',
                          'street_number2',
                          'l10n_mx_edi_colony',
                          'l10n_mx_edi_locality',
                          'city',
                          'state_id',
                          'country_id',
                          'zip']
        for field in address_fields:
            if getattr(partner_id, field):
                return True
        return False

    @api.multi
    def l10n_mx_edi_is_required(self):
        self.ensure_one()
        return (self.type in ('out_invoice', 'out_refund') and
                self.company_id.country_id == self.env.ref('base.mx'))

    @api.multi
    def l10n_mx_edi_log_error(self, message):
        self.ensure_one()
        self.message_post(body=_('Error during the process: %s') % message, subtype='account.mt_invoice_validated')

    # -------------------------------------------------------------------------
    # SAT/PAC service methods
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_mx_edi_solfact_info(self, company_id, service_type):
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
    def _l10n_mx_edi_solfact_sign(self, pac_info):
        '''SIGN for Solucion Factible.
        '''
        url = pac_info['url']
        username = pac_info['username']
        password = pac_info['password']
        for inv in self:
            cfdi = inv.l10n_mx_edi_cfdi
            try:
                client = Client(url, timeout=20)
                response = client.service.timbrar(username, password, cfdi, False)
            except Exception as e:
                inv.l10n_mx_edi_log_error(e.message)
                continue
            msg = getattr(response.resultados[0], 'mensaje', None)
            code = getattr(response.resultados[0], 'status', None)
            xml_signed = getattr(response.resultados[0], 'cfdiTimbrado', None)
            inv._l10n_mx_edi_post_sign_process(xml_signed, code, msg)

    @api.multi
    def _l10n_mx_edi_solfact_cancel(self, pac_info):
        '''CANCEL for Solucion Factible.
        '''
        url = pac_info['url']
        username = pac_info['username']
        password = pac_info['password']
        for inv in self:
            uuids = [inv.l10n_mx_edi_cfdi_uuid]
            certificate_id = inv.l10n_mx_edi_cfdi_certificate_id
            cer_pem = base64.encodestring(certificate_id.get_pem_cer(certificate_id.content))
            key_pem = base64.encodestring(certificate_id.get_pem_key(certificate_id.key, certificate_id.password))
            key_password = certificate_id.password
            try:
                client = Client(url, timeout=20)
                response = client.service.cancelar(username, password, uuids, cer_pem, key_pem, key_password)
            except Exception as e:
                inv.l10n_mx_edi_log_error(e.message)
                continue
            msg = getattr(response.resultados[0], 'mensaje', None)
            code = getattr(response.resultados[0], 'statusUUID', None)
            cancelled = code == '201' or code == '202'
            inv._l10n_mx_edi_post_cancel_process(cancelled, code, msg)

    @api.multi
    def _l10n_mx_edi_finkok_info(self, company_id, service_type):
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
    def _l10n_mx_edi_finkok_sign(self, pac_info):
        '''SIGN for Finkok.
        '''
        url = pac_info['url']
        username = pac_info['username']
        password = pac_info['password']
        for inv in self:
            cfdi = [inv.l10n_mx_edi_cfdi]
            try:
                client = Client(url, timeout=20)
                response = client.service.stamp(cfdi, username, password)
            except Exception as e:
                inv.l10n_mx_edi_log_error(e.message)
                continue
            code = 0
            msg = None
            if response.Incidencias:
                code = getattr(response.Incidencias[0][0], 'CodigoError', None)
                msg = getattr(response.Incidencias[0][0], 'MensajeIncidencia', None)
            xml_signed = getattr(response, 'xml', None)
            if xml_signed:
                xml_signed = xml_signed.encode('utf-8').encode('base64')
            inv._l10n_mx_edi_post_sign_process(xml_signed, code, msg)

    @api.multi
    def _l10n_mx_edi_finkok_cancel(self, pac_info):
        '''CANCEL for Finkok.
        '''
        url = pac_info['url']
        username = pac_info['username']
        password = pac_info['password']
        for inv in self:
            uuid = inv.l10n_mx_edi_cfdi_uuid
            certificate_id = inv.l10n_mx_edi_cfdi_certificate_id
            company_id = self.company_id
            cer_pem = base64.encodestring(certificate_id.get_pem_cer(certificate_id.content))
            key_pem = base64.encodestring(certificate_id.get_pem_key(certificate_id.key, certificate_id.password))
            try:
                client = Client(url, timeout=20)
                invoices_list = client.factory.create("UUIDS")
                invoices_list.uuids.string = [uuid]
                response = client.service.cancel(invoices_list, username, password, company_id.vat, cer_pem, key_pem)
            except Exception as e:
                inv.l10n_mx_edi_log_error(e.message)
                continue
            if not hasattr(response, 'Folios'):
                msg = _('A delay of 2 hours has to be respected before to cancel')
            else:
                code = getattr(response.Folios[0][0], 'EstatusUUID', None)
                cancelled = code == '201' or code == '202'  # cancelled or previously cancelled
                msg = code != 201 and code != 202 and "Cancelling get an error"
            inv._l10n_mx_edi_post_cancel_process(cancelled, code, msg)

    @api.multi
    def l10n_mx_edi_get_pac_version(self, pac_name):
        '''Returns the cfdi version of the pac. By default, the version is 3.2.
        '''
        return "3.2"

    @api.multi
    def _l10n_mx_edi_call_service(self, service_type):
        '''Call the right method according to the pac_name, it's info returned by the '_l10n_mx_edi_%s_info' % pac_name'
        method and the service_type passed as parameter.

        :param service_type: sign or cancel
        '''
        # Regroup the invoices by company (= by pac)
        comp_x_records = groupby(self, lambda r: r.company_id)
        for company_id, records in comp_x_records:
            pac_name = company_id.l10n_mx_edi_pac
            if not pac_name:
                continue
            # Get the informations about the pac
            pac_info_func = '_l10n_mx_edi_%s_info' % pac_name
            service_func = '_l10n_mx_edi_%s_%s' % (pac_name, service_type)
            pac_info = getattr(self, pac_info_func)(company_id, service_type)
            # Call the service with invoices one by one or all together according to the 'multi' value.
            multi = pac_info.pop('multi', False)
            if multi:
                # rebuild the recordset
                records = self.env['account.invoice'].search(
                    [('id', 'in', self.ids), ('company_id', '=', company_id.id)])
                getattr(records, service_func)(pac_info)
            else:
                for record in records:
                    getattr(record, service_func)(pac_info)

    @api.multi
    def _l10n_mx_edi_post_sign_process(self, xml_signed, code=None, msg=None):
        '''Post process the results of the sign service.

        :param xml_signed: the xml signed datas codified in base64
        :param code: an eventual error code
        :param msg: an eventual error msg
        '''
        self.ensure_one()
        if xml_signed:
            body_msg = _('The sign service has been called with success')
            # Update the pac status
            self.l10n_mx_edi_pac_status = 'signed'
            self.l10n_mx_edi_cfdi = xml_signed
            # Update the content of the attachment
            attachment_id = self.l10n_mx_edi_retrieve_last_attachment()
            attachment_id.write({
                'datas': xml_signed,
                'mimetype': 'application/xml'
            })
            post_msg = [_('The content of the attachment has been updated')]
        else:
            body_msg = _('The sign service requested failed')
            post_msg = []
        if code:
            post_msg.extend([_('Code: ') + str(code)])
        if msg:
            post_msg.extend([_('Message: ') + msg])
        self.message_post(
            body=body_msg + create_list_html(post_msg),
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
    def _l10n_mx_edi_post_cancel_process(self, cancelled, code=None, msg=None):
        '''Post process the results of the cancel service.

        :param cancelled: is the cancel has been done with success
        :param code: an eventual error code
        :param msg: an eventual error msg
        '''

        self.ensure_one()
        if cancelled:
            body_msg = _('The cancel service has been called with success')
            self.l10n_mx_edi_pac_status = 'cancelled'
        else:
            body_msg = _('The cancel service requested failed')
        post_msg = []
        if code:
            post_msg.extend([_('Code: ') + str(code)])
        if msg:
            post_msg.extend([_('Message: ') + msg])
        self.message_post(
            body=body_msg + create_list_html(post_msg),
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
                record.message_post(body=_('The cancel service has been called with success'),
                    subtype='account.mt_invoice_validated')
            else:
                record.l10n_mx_edi_pac_status = 'to_cancel'
        records = self.search([
            ('l10n_mx_edi_pac_status', '=', 'to_cancel'),
            ('id', 'in', self.ids)])
        records._l10n_mx_edi_call_service('cancel')

    # -------------------------------------------------------------------------
    # Account invoice methods
    # -------------------------------------------------------------------------

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        '''Set the payment bank account on the invoice as the first of the selected partner.
        '''
        res = super(AccountInvoice, self)._onchange_partner_id()
        if self.commercial_partner_id.bank_ids:
            self.l10n_mx_edi_partner_bank_id = self.commercial_partner_id.bank_ids[0].id
        return res

    @api.multi
    @api.depends('l10n_mx_edi_cfdi_name')
    def _compute_cfdi_values(self):
        '''Fill the invoice fields from the cfdi values.
        '''
        for inv in self:
            attachment_id = inv.l10n_mx_edi_retrieve_last_attachment()
            if not attachment_id:
                continue
            # At this moment, the attachment contains the file size in its 'datas' field because
            # to save some memory, the attachment will store its data on the physical disk.
            # To avoid this problem, we read the 'datas' directly on the disk.
            datas = attachment_id._file_read(attachment_id.store_fname)
            inv.l10n_mx_edi_cfdi = datas
            tree = inv.l10n_mx_edi_get_xml_etree(base64.decodestring(datas))
            # if already signed, extract uuid
            tfd_node = inv.l10n_mx_edi_get_tfd_etree(tree)
            if tfd_node is not None:
                inv.l10n_mx_edi_cfdi_uuid = tfd_node.get('UUID')
            inv.l10n_mx_edi_cfdi_amount = tree.get('total')
            inv.l10n_mx_edi_cfdi_supplier_rfc = tree.Emisor.get('rfc')
            inv.l10n_mx_edi_cfdi_customer_rfc = tree.Receptor.get('rfc')
            inv.l10n_mx_edi_cfdi_certificate_id = self.env['l10n_mx_edi.certificate'].sudo().search(
                [('serial_number', '=', tree.attrib['noCertificado'])], limit=1)

    @api.multi
    def _l10n_mx_edi_create_taxes_cfdi_values(self):
        '''Create the taxes values to fill the CFDI template.
        '''
        self.ensure_one()
        values = {
            'total_withhold': 0,
            'total_transferred': 0,
            'withholding': [],
            'transferred': [],
        }
        for tax in self.tax_line_ids:
            tax_dict = {
                'name': (tax.tax_id.tag_ids[0].name
                         if tax.tax_id.tag_ids else tax.tax_id.name).upper(),
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
        amount_untaxed = sum(self.invoice_line_ids.mapped(lambda l: l.quantity * l.price_unit))
        amount_discount = sum(self.invoice_line_ids.mapped(lambda l: l.quantity * l.price_unit * l.discount / 100.0))
        values = {
            'record': self,
            'currency_name': self.currency_id.name,
            'supplier': self.company_id.partner_id.commercial_partner_id,
            'issued': self.journal_id.l10n_mx_address_issued_id,
            'customer': self.partner_id.commercial_partner_id,
            'number': self.number,
            'fiscal_position': self.company_id.partner_id.property_account_position_id.name,
            'payment_method': self.l10n_mx_edi_payment_method_id.code,
            'amount_total': '%0.*f' % (precision_digits, self.amount_total),
            'amount_untaxed': '%0.*f' % (precision_digits, amount_untaxed),
            'amount_discount': '%0.*f' % (precision_digits, amount_discount) if amount_discount else None,
        }

        ctx = dict(company_id=self.company_id.id, date=self.date_invoice)
        mxn = self.env.ref('base.MXN').with_context(ctx)
        invoice_currency = self.currency_id.with_context(ctx)
        values['rate'] = '%0.*f' % (precision_digits, invoice_currency.compute(1, mxn))

        values['document_type'] = 'ingreso' if self.type == 'out_invoice' else 'egreso'

        if len(self.payment_term_id.line_ids) > 1:
            values['payment_policy'] = 'Pago en parcialidades'
        else:
            values['payment_policy'] = 'Pago en una sola exhibición'

        values['domicile'] = '%s %s, %s' % (
            self.company_id.city,
            self.company_id.state_id.name,
            self.company_id.country_id.name,
        )

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
        tree = self.l10n_mx_edi_get_xml_etree(cfdi)
        cadena = self.l10n_mx_edi_generate_cadena(CFDI_XSLT_CADENA % version, tree)

        # Post append cadena
        tree.attrib['sello'] = certificate_id.sudo().get_encrypted_cadena(cadena)

        # Check with xsd
        try:
            check_with_xsd(tree, CFDI_XSD % version)
        except Exception as e:
            return {'error': _('The cfdi generated is not valid') + create_list_html(e.name.split('\n'))}

        # Post append addenda
        if self.partner_id.l10n_mx_edi_addenda:
            cfdi_addenda_node = tree.Addenda
            addenda_tree = etree.fromstring(self.partner_id.l10n_mx_edi_addenda.arch, parser=parser)
            addenda_str = qweb.render(addenda_tree, values=values)
            addenda_node = etree.fromstring(addenda_str, parser=parser)
            cfdi_addenda_node.extend(addenda_node)

        return {'cfdi': etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')}

    @api.multi
    def _l10n_mx_edi_retry(self):
        '''Try to generate the cfdi attachment and then, sign it.
        '''
        for inv in self:
            cfdi_values = inv._l10n_mx_edi_create_cfdi()
            error = cfdi_values.pop('error', None)
            cfdi = cfdi_values.pop('cfdi', None)
            if error:
                # cfdi failed to be generated
                inv.l10n_mx_edi_pac_status = 'retry'
                inv.message_post(body=error, subtype='account.mt_invoice_validated')
                continue
            # cfdi has been successfully generated
            inv.l10n_mx_edi_pac_status = 'to_sign'
            filename = ('%s-MX-Invoice-2.1.xml' % inv.number).replace('/', '')
            ctx = self.env.context.copy()
            ctx.pop('default_type', False)
            inv.l10n_mx_edi_cfdi_name = filename
            attachment_id = self.env['ir.attachment'].with_context(ctx).create({
                'name': filename,
                'res_id': inv.id,
                'res_model': inv._name,
                'datas': base64.encodestring(cfdi),
                'datas_fname': filename,
                'description': 'Mexican invoice',
                })
            inv.message_post(
                body=_('CFDI document generated (may be not signed)'),
                attachment_ids=[attachment_id.id],
                subtype='account.mt_invoice_validated')
            inv._l10n_mx_edi_sign()

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
        '''Cancel the cfdi attachments for mexican companies when cancelled.
        '''
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
        url = 'https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc?wsdl'
        for inv in self:
            if self.l10n_mx_edi_pac_status not in ['signed', 'cancelled']:
                continue
            supplier_rfc = inv.l10n_mx_edi_cfdi_supplier_rfc
            customer_rfc = inv.l10n_mx_edi_cfdi_customer_rfc
            total = inv.l10n_mx_edi_cfdi_amount
            uuid = inv.l10n_mx_edi_cfdi_uuid
            params = url_encode({'re': supplier_rfc, 'rr': customer_rfc, 'tt': total, 'id': uuid})
            try:
                client = Client(url)
                response = client.service.Consulta(params).Estado
            except Exception as e:
                inv.l10n_mx_edi_log_error(e.message or e.reason.__repr__())
                continue
            inv.l10n_mx_edi_sat_status = CFDI_SAT_QR_STATE.get(response.__repr__(), 'none')
