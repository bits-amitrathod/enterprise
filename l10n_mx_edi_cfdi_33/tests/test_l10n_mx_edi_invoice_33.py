# coding: utf-8

import base64
import os
import datetime

from lxml import etree, objectify

from odoo.tools import misc

from odoo.addons.l10n_mx_edi.tests import common


class TestL10nMxEdiInvoice33(common.InvoiceTransactionCase):

    def setUp(self):
        super(TestL10nMxEdiInvoice33, self).setUp()
        self.refund_model = self.env['account.invoice.refund']
        self.register_payments_model = self.env['account.register.payments']
        self.payment_model = self.env['account.payment']

        self.cert = misc.file_open(os.path.join(
            'l10n_mx_edi', 'demo', 'pac_credentials', 'certificate.cer'), 'rb').read()
        self.cert_key = misc.file_open(os.path.join(
            'l10n_mx_edi', 'demo', 'pac_credentials', 'certificate.key'), 'rb').read()
        self.cert_password = '12345678a'
        self.xml_expected_str = misc.file_open(os.path.join(
            'l10n_mx_edi_cfdi_33', 'tests', 'expected_cfdi33.xml')).read().encode('UTF-8')
        self.xml_expected = objectify.fromstring(self.xml_expected_str)
        self.l10n_mx_edi_basic_configuration()
        self.company_partner = self.env.ref('base.main_partner')
        self.payment_term = self.ref('account.account_payment_term_net')
        self.config_parameter = self.env.ref(
            'l10n_mx_edi_cfdi_33.l10n_mx_edi_version_cfdi')
        self.config_parameter.value = '3.3'
        self.fiscal_position.l10n_mx_edi_code = '601'
        self.product.l10n_mx_edi_code_sat_id = self.ref(
            'l10n_mx_edi_cfdi_33.prod_code_sat_01010101')
        self.tax_positive.l10n_mx_cfdi_tax_type = 'Tasa'
        self.tax_negative.l10n_mx_cfdi_tax_type = 'Tasa'
        isr_tag = self.env['account.account.tag'].search(
            [('name', '=', 'ISR')])
        self.tax_negative.tag_ids |= isr_tag
        self.payment_method_manual_out = self.env.ref("account.account_payment_method_manual_out")

    def l10n_mx_edi_basic_configuration(self):
        self.company.write({
            'currency_id': self.mxn.id,
            'name': 'YourCompany',
        })
        self.company.partner_id.write({
            'vat': 'ACO560518KW7',
            'country_id': self.env.ref('base.mx').id,
            'zip': '37200',
            'property_account_position_id': self.fiscal_position.id,
        })
        self.account_settings.create({
            'l10n_mx_edi_pac': 'finkok',
            'l10n_mx_edi_pac_test_env': True,
            'l10n_mx_edi_certificate_ids': [{
                'content': base64.encodestring(self.cert),
                'key': base64.encodestring(self.cert_key),
                'password': self.cert_password,
            }]
        }).execute()
        self.set_currency_rates(mxn_rate=21, usd_rate=1)

    def test_l10n_mx_edi_invoice_basic(self):
        # -----------------------
        # Testing sign process
        # -----------------------
        invoice = self.create_invoice()
        invoice.move_name = 'INV/2017/999'
        invoice.action_invoice_open()
        self.assertEqual(invoice.state, "open")
        self.assertEqual(invoice.l10n_mx_edi_pac_status, "signed",
                         invoice.message_ids.mapped('body'))
        xml = invoice.l10n_mx_edi_get_xml_etree()
        self.xml_merge_dynamic_items(xml, self.xml_expected)
        self.assertEqualXML(xml, self.xml_expected)
        xml_attach = base64.decodestring(invoice.l10n_mx_edi_cfdi)
        self.assertEqual(xml_attach.splitlines()[0].lower(),
                         b'<?xml version="1.0" encoding="utf-8"?>'.lower())

        # ----------------
        # Testing discount
        # ----------------
        invoice_disc = invoice.copy()
        for line in invoice_disc.invoice_line_ids:
            line.discount = 10
            line.price_unit = 500
        invoice_disc.compute_taxes()
        invoice_disc.action_invoice_open()
        self.assertEqual(invoice_disc.state, "open")
        self.assertEqual(invoice_disc.l10n_mx_edi_pac_status, "signed",
                         invoice.message_ids.mapped('body'))
        xml = invoice_disc.l10n_mx_edi_get_xml_etree()
        xml_expected_disc = objectify.fromstring(self.xml_expected_str)
        xml_expected_disc.attrib['SubTotal'] = '500.00'
        xml_expected_disc.attrib['Descuento'] = '50.00'
        # 500 - 10% + taxes(16%, -10%)
        xml_expected_disc.attrib['Total'] = '477.00'
        xml_expected_disc.attrib['Folio'] = xml.attrib['Folio']
        xml_expected_disc.attrib['Serie'] = xml.attrib['Serie']
        self.xml_merge_dynamic_items(xml, xml_expected_disc)
        for concepto in xml_expected_disc.Conceptos:
            concepto.Concepto.attrib['ValorUnitario'] = '500.00'
            concepto.Concepto.attrib['Importe'] = '500.00'
            concepto.Concepto.attrib['Descuento'] = '50.00'
        self.assertEqualXML(xml, xml_expected_disc)

        # -----------------------
        # Testing cancel PAC process
        # -----------------------
        invoice.sudo().journal_id.update_posted = True
        invoice.action_invoice_cancel()
        self.assertEqual(invoice.state, "cancel")
        self.assertEqual(invoice.l10n_mx_edi_pac_status, 'cancelled',
                         invoice.message_ids.mapped('body'))
        invoice.l10n_mx_edi_pac_status = "signed"

        # -----------------------
        # Testing cancel SAT process
        # -----------------------
        invoice.l10n_mx_edi_update_sat_status()
        self.assertNotEqual(invoice.l10n_mx_edi_sat_status, "cancelled")

    def test_l10n_mx_edi_invoice_basic_33(self):
        isr_tag = self.env['account.account.tag'].search(
            [('name', '=', 'ISR')])
        self.tax_negative.tag_ids |= isr_tag
        self.test_l10n_mx_edi_invoice_basic()

        # -----------------------
        # Testing invoice refund to verify CFDI related section
        # -----------------------
        invoice = self.create_invoice()
        invoice.action_invoice_open()
        refund = self.refund_model.with_context(
            active_ids=invoice.ids).create({
                'filter_refund': 'refund',
                'description': 'Refund Test',
                'date': invoice.date_invoice,
            })
        result = refund.invoice_refund()
        refund_id = result.get('domain')[1][2]
        refund = self.invoice_model.browse(refund_id)
        refund.action_invoice_open()
        xml = refund.l10n_mx_edi_get_xml_etree()
        self.assertEquals(xml.CfdiRelacionados.CfdiRelacionado.get('UUID'),
                          invoice.l10n_mx_edi_cfdi_uuid,
                          'Invoice UUID is different to CFDI related')

    def test_l10n_mx_edi_account_payment(self):
        """Generated two payments to an invoice, to test
        the payment complement.
        """
        self.config_parameter.value = '3.3'

        self.xml_expected_str = misc.file_open(os.path.join(
            'l10n_mx_edi_cfdi_33', 'tests', 'expected_payment.xml')).read().encode('UTF-8')
        self.xml_expected = objectify.fromstring(self.xml_expected_str)

        journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        invoice = self.create_invoice()
        today = self.env['l10n_mx_edi.certificate'].sudo().get_mx_current_datetime()
        invoice.date_invoice = today - datetime.timedelta(days=1)
        invoice.move_name = 'INV/2017/999'

        invoice.action_invoice_open()
        self.assertEqual(invoice.state, "open")
        self.assertEqual(invoice.l10n_mx_edi_pac_status, "signed",
                         invoice.message_ids.mapped('body'))

        ctx = {'active_model': 'account.invoice', 'active_ids': [invoice.id]}
        register_payments = self.register_payments_model.with_context(ctx).create({
            'payment_date': today,
            'l10n_mx_edi_payment_method_id': self.payment_method_cash.id,
            'payment_method_id': self.payment_method_manual_out.id,
            'journal_id': journal.id,
            'communication': invoice.number,
            'amount': 238.5,
        })

        # First payment
        register_payments.create_payment()
        payment = invoice.payment_ids
        self.assertEqual(
            payment.l10n_mx_edi_pac_status, 'signed', payment.message_ids.mapped('body'))

        # Last payment
        register_payments.create_payment()
        payment = invoice.payment_ids - payment
        self.assertEqual(
            payment.l10n_mx_edi_pac_status, 'signed', payment.message_ids.mapped('body'))
        self.assertEqual(invoice.state, 'paid')

        xml = payment.l10n_mx_edi_get_xml_etree()
        self.xml_merge_dynamic_items(xml, self.xml_expected)
        self.xml_expected.attrib['Folio'] = xml.attrib['Folio']
        self.assertEqualXML(xml, self.xml_expected)

    def xml_merge_dynamic_items(self, xml, xml_expected):
        if xml.get('version', xml.get('Version')) == '3.2':
            return super(TestL10nMxEdiInvoice33, self).xml_merge_dynamic_items()
        xml_expected.attrib['Fecha'] = xml.attrib['Fecha']
        xml_expected.attrib['Sello'] = xml.attrib['Sello']

        # Set elements dynamic of Pagos node
        payment = self.payment_model.l10n_mx_edi_get_payment_etree(xml)
        # Use 'len(elem)' when elem is a lxml.etree._Element to avoid FutureWarning
        if len(payment):
            payment_expected = self.payment_model.l10n_mx_edi_get_payment_etree(
                xml_expected)
            payment_expected[0].getparent().set(
                'FechaPago', payment[0].getparent().get('FechaPago', ''))
            payment_expected[0].set(
                'IdDocumento', payment[0].get('IdDocumento'))

        # Replace node TimbreFiscalDigital
        tfd_expected = self.invoice_model.l10n_mx_edi_get_tfd_etree(
            xml_expected)
        tfd_xml = objectify.fromstring(etree.tostring(
            self.invoice_model.l10n_mx_edi_get_tfd_etree(xml)))
        xml_expected.Complemento.replace(tfd_expected, tfd_xml)
