# -*- coding: utf-8 -*-

import base64
import re
import logging

from lxml import etree
from suds.client import Client

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_mx_edi.models import account_invoice

CFDI_TEMPLATE = 'l10n_mx_edi_cfdi_33.cfdiv33'
CFDI_XSLT_CADENA = 'l10n_mx_edi_cfdi_33/data/%s/cadenaoriginal.xslt'

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    l10n_mx_edi_usage = fields.Selection([
        ('G01', 'Acquisition of merchandise'),
        ('G02', 'Returns, discounts or bonuses'),
        ('G03', 'General expenses'),
        ('I01', 'Constructions'),
        ('I02', 'Office furniture and equipment investment'),
        ('I03', 'Transportation equipment'),
        ('I04', 'Computer equipment and accessories'),
        ('I05', 'Dices, dies, molds, matrices and tooling'),
        ('I06', 'Telephone communications'),
        ('I07', 'Satellite communications'),
        ('I08', 'Other machinery and equipment'),
        ('D01', 'Medical, dental and hospital expenses.'),
        ('D02', 'Medical expenses for disability'),
        ('D03', 'Funeral expenses'),
        ('D04', 'Donations'),
        ('D05', 'Real interest effectively paid for mortgage loans (room house)'),
        ('D06', 'Voluntary contributions to SAR'),
        ('D07', 'Medical insurance premiums'),
        ('D08', 'Mandatory School Transportation Expenses'),
        ('D09', 'Deposits in savings accounts, premiums based on pension plans.'),
        ('D10', 'Payments for educational services (Colegiatura)'),
        ('P01', 'To define'),
    ], 'Usage', default='P01',
        help='Used in CFDI 3.3 to express the key to the usage that will '
        'gives the receiver to this invoice. This value is defined by the '
        'customer. \nNote: It is not cause for cancellation if the key set is '
        'not the usage that will give the receiver of the document.')
    l10n_mx_edi_origin = fields.Char(
        string='CFDI Origin', copy=False,
        help='In some cases like payments, credit notes, debit notes, '
        'invoices re-signed or invoices that are redone due to payment in '
        'advance will need this field filled, the format is: \nOrigin Type|'
        'UUID1, UUID2, ...., UUIDn.\nWhere the origin type could be:\n'
        '- 01: Nota de crédito\n'
        '- 02: Nota de débito de los documentos relacionados\n'
        '- 03: Devolución de mercancía sobre facturas o traslados previos\n'
        '- 04: Sustitución de los CFDI previos\n'
        '- 05: Traslados de mercancias facturados previamente\n'
        '- 06: Factura generada por los traslados previos\n'
        '- 07: CFDI por aplicación de anticipo')

    @api.multi
    @api.depends('l10n_mx_edi_cfdi_name')
    def _compute_cfdi_values(self):
        """Fill the invoice fields from the cfdi values."""
        version = self.l10n_mx_edi_get_pac_version('')
        if version == '3.2':
            return super(AccountInvoice, self)._compute_cfdi_values()
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
            inv.l10n_mx_edi_cfdi_amount = tree.get('total', tree.get('Total'))
            inv.l10n_mx_edi_cfdi_supplier_rfc = tree.Emisor.get('rfc', tree.Emisor.get('Rfc'))
            inv.l10n_mx_edi_cfdi_customer_rfc = tree.Receptor.get('rfc', tree.Receptor.get('Rfc'))
            certificate = tree.get('noCertificado', tree.get('NoCertificado'))
            inv.l10n_mx_edi_cfdi_certificate_id = self.env['l10n_mx_edi.certificate'].sudo().search(
                [('serial_number', '=', certificate)], limit=1)

    @api.multi
    def _l10n_mx_edi_create_cfdi_values(self):
        self.ensure_one()
        values = super(AccountInvoice, self)._l10n_mx_edi_create_cfdi_values()
        version = self.l10n_mx_edi_get_pac_version('')
        if version == '3.2':
            return values
        precision_digits = self.env['decimal.precision'].precision_get('Account')
        values['decimal_precision'] = precision_digits
        values['total_discount'] = lambda l, d: ('%.*f' % (
            int(d), l.quantity * l.price_unit * l.discount / 100)) if l.discount else False
        values['tax_name'] = lambda t: {'ISR': '001', 'IVA': '002', 'IEPS': '003'}.get(
            t, False)
        values['fiscal_position'] = self.company_id.partner_id.property_account_position_id
        values['use_cfdi'] = self.l10n_mx_edi_usage
        values['conditions'] = self._get_string_cfdi(
            self.payment_term_id.name, 1000) if self.payment_term_id else False
        values['rate'] = False if self.currency_id.name == 'MXN' else values.get('rate', False)
        term_ids = self.payment_term_id.line_ids
        values['payment_policy'] = 'PPD' if term_ids.search(
            [('days', '>', 0), ('id', 'in', term_ids.ids)], limit=1) else 'PUE'
        return values

    @api.multi
    def _l10n_mx_edi_create_cfdi(self):
        self.ensure_one()
        version = self.l10n_mx_edi_get_pac_version('')
        if version == '3.2':
            return super(AccountInvoice, self)._l10n_mx_edi_create_cfdi()
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
            return {'error': _('Please check your configuration: ') + account_invoice.create_list_html(error_log)}

        # -----------------------
        # Create the EDI document
        # -----------------------

        # -Compute certificate data
        values['date'] = certificate_id.sudo().get_mx_current_datetime().strftime('%Y-%m-%dT%H:%M:%S')
        values['certificate_number'] = certificate_id.serial_number
        values['certificate'] = certificate_id.sudo().get_data()[0]

        # -Compute cfdi
        if version == '3.3':
            cfdi = qweb.render(CFDI_TEMPLATE, values=values)
        else:
            return {'error': _('Unsupported version %s') % version}

        # -Compute cadena
        tree = self.l10n_mx_edi_get_xml_etree(cfdi)
        cadena = self.l10n_mx_edi_generate_cadena(CFDI_XSLT_CADENA % version, tree)
        tree.attrib['Sello'] = certificate_id.sudo().get_encrypted_cadena(cadena)

        return {'cfdi': etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')}

    @api.multi
    def l10n_mx_edi_get_pac_version(self, pac_name):
        """Returns the cfdi version to generate the CFDI.
        In December, 1, 2017 the CFDI 3.2 is deprecated, after July 1, 2017
        the CFDI 3.3 could be used."""
        # Overwritten the method, because the original only return a value cabling
        version = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_mx_edi_cfdi_version', '3.3')
        return version

    @api.model
    def _get_l10n_mx_edi_cadena(self):
        self.ensure_one()
        version = self.l10n_mx_edi_get_pac_version('')
        if version == '3.2':
            return super(AccountInvoice, self)._get_l10n_mx_edi_cadena()
        xslt_path = CFDI_XSLT_CADENA % version
        #get the cfdi as eTree
        cfdi = base64.decodestring(self.l10n_mx_edi_cfdi)
        cfdi = self.l10n_mx_edi_get_xml_etree(cfdi)
        #return the cadena
        return self.l10n_mx_edi_generate_cadena(xslt_path, cfdi)

    __check_cfdi_re = re.compile(u'''([A-Z]|[a-z]|[0-9]| |Ñ|ñ|!|"|%|&|'|´|-|:|;|>|=|<|@|_|,|\{|\}|`|~|á|é|í|ó|ú|Á|É|Í|Ó|Ú|ü|Ü)''')

    @staticmethod
    def _get_string_cfdi(text, size=100):
        """Replace from text received the characters that are not found in the
        regex. This regex is taken from SAT documentation
        https://goo.gl/C9sKH6
        text: Text to remove extra characters
        size: Cut the string in size len
        Ex. 'Product ABC (small size)' - 'Product ABC small size'"""
        for char in AccountInvoice.__check_cfdi_re.sub('', text):
            text = text.replace(char, ' ')
        return text.strip()[:size]

    @api.multi
    def get_cfdi_related(self):
        """To node CfdiRelacionados get documents related with each invoice
        from l10n_mx_edi_origin, hope the next structure:
            relation type|UUIDs separated by ,"""
        self.ensure_one()
        if not self.l10n_mx_edi_origin:
            return {}
        origin = self.l10n_mx_edi_origin.split('|')
        uuids = origin[1].split(',') if len(origin) > 1 else []
        return {
            'type': origin[0],
            'related': [u.strip() for u in uuids],
            }

    @api.multi
    def action_invoice_draft(self):
        """Set l10n_mx_edi_origin when invoice state set to draft"""

        if self.l10n_mx_edi_get_pac_version('') == '3.3':
            for record in self.filtered('l10n_mx_edi_cfdi_uuid'):
                record.l10n_mx_edi_origin = self._set_cfdi_origin('04', [record.l10n_mx_edi_cfdi_uuid])
        return super(AccountInvoice, self).action_invoice_draft()

    @api.multi
    def _get_total_invoice(self, payment):
        self.ensure_one()
        if self.payment_move_line_ids:
            currency_id = self.currency_id
            for payment in self.payment_move_line_ids.filtered(lambda m: m in payment.move_line_ids):
                payment_currency_id = False
                if self.type in ('out_invoice', 'in_refund'):
                    amount = sum([p.amount for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                    if payment.matched_debit_ids:
                        payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in payment.matched_debit_ids]) and payment.matched_debit_ids[0].currency_id or False
                # get the payment value in invoice currency
                if payment_currency_id and payment_currency_id == self.currency_id:
                    return amount_currency
                return payment.company_id.currency_id.with_context(date=payment.date).compute(amount, self.currency_id)

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None,
                        description=None, journal_id=None):
        """When is created the invoice refund is assigned the reference to
        the invoice that was generate it"""
        values = super(AccountInvoice, self)._prepare_refund(
            invoice, date_invoice=date_invoice, date=date,
            description=description, journal_id=journal_id)
        if invoice.l10n_mx_edi_cfdi_uuid:
            values['l10n_mx_edi_origin'] = self._set_cfdi_origin('01', [invoice.l10n_mx_edi_cfdi_uuid])
        return values

    @api.multi
    def _set_cfdi_origin(self, rtype='', uuids=[]):
        """Try to write the origin in of the CFDI, it is important in order
        to have a centralized way to manage this elements due to the fact
        that this logic can be used in several places functionally speaking
        all around Odoo.
        :param rtype:
            - 01: Nota de crédito
            - 02: Nota de débito de los documentos relacionados
            - 03: Devolución de mercancía sobre facturas o traslados previos
            - 04: Sustitución de los CFDI previos
            - 05: Traslados de mercancias facturados previamente
            - 06: Factura generada por los traslados previos
            - 07: CFDI por aplicación de anticipo
        :param uuids:
        :return:
        """
        self.ensure_one()
        types = ['01', '02', '03', '04', '05', '06', '07']
        if rtype not in types:
            raise UserError(_('Invalid given type of document for field CFDI '
                              'Origin'))
        ids = ','.join(uuids)
        l10n_mx_edi_origin = self.l10n_mx_edi_origin
        old_rtype = l10n_mx_edi_origin.split('|')[0] if l10n_mx_edi_origin else False
        if old_rtype and old_rtype not in types:
            raise UserError(_('Invalid type of document for field CFDI '
                              'Origin'))
        if not l10n_mx_edi_origin or old_rtype != rtype:
            origin = '%s|%s' % (rtype, ids)
            self.update({'l10n_mx_edi_origin': origin})
            return origin
        try:
            old_ids = l10n_mx_edi_origin.split('|')[1].split(',')
        except IndexError:
            raise UserError(
                _('The cfdi origin field must be filled with type and list of '
                  'cfdi separated by comma like this '
                  '"01|89966ACC-0F5C-447D-AEF3-3EED22E711EE,89966ACC-0F5C-447D-AEF3-3EED22E711EE"'
                  '\n get %s instead' % l10n_mx_edi_origin))
        ids = ','.join(old_ids + uuids)
        origin = '%s|%s' % (rtype, ids)
        self.update({'l10n_mx_edi_origin': origin})
        return origin

    @api.multi
    def _l10n_mx_edi_finkok_sign(self, pac_info):
        """Get message error Finkok"""
        res = super(AccountInvoice, self)._l10n_mx_edi_finkok_sign(pac_info)
        not_sign = self.filtered(lambda i: i.l10n_mx_edi_pac_status != 'signed')
        if not not_sign:
            return res
        url = pac_info['url']
        username = pac_info['username']
        password = pac_info['password']
        for inv in not_sign:
            cfdi = [inv.l10n_mx_edi_cfdi.decode('UTF-8')]
            try:
                client = Client(url, timeout=20)
                response = client.service.stamp(cfdi, username, password)
            except Exception as e:
                inv.l10n_mx_edi_log_error(str(e))
                continue
            code = 0
            msg = None
            if response.Incidencias:
                code = getattr(response.Incidencias[0][0], 'CodigoError', None)
                msg = getattr(response.Incidencias[0][0], 'MensajeIncidencia' if code != '301' else 'ExtraInfo', None)
            if code == '301':
                inv._l10n_mx_edi_post_sign_process(False, code, msg)
        return res

    @api.multi
    def _l10n_mx_edi_create_taxes_cfdi_values(self):
        """Complete the taxes values to fill the CFDI template."""
        self.ensure_one()
        values = super(AccountInvoice, self)._l10n_mx_edi_create_taxes_cfdi_values()
        for tax in values.get('transferred', []):
            line = self.tax_line_ids.filtered(lambda t: t.tax_id and round(
                abs(t.amount or 0.0), 2) == tax.get('amount', 0.0) and round(
                    abs(t.tax_id.amount), 2) == tax.get('rate', 0.0))
            tax.update({'type': line.tax_id.l10n_mx_cfdi_tax_type})
        return values
