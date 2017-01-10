# coding: utf-8

import base64

from lxml import etree

from odoo.modules.module import get_module_resource

from . import common


class TestL10nMxEdiInvoice(common.InvoiceTransactionCase):
    def setUp(self):
        super(TestL10nMxEdiInvoice, self).setUp()
        self.cert_path = get_module_resource(
            'l10n_mx_edi', 'demo', 'pac_credentials', 'certificate.cer')
        self.cert_key_path = get_module_resource(
            'l10n_mx_edi', 'demo', 'pac_credentials', 'certificate.key')
        self.cert = open(self.cert_path, "rb").read()
        self.cert_key = open(self.cert_key_path, "rb").read()
        self.cert_password = '12345678a'
        self.l10n_mx_edi_basic_configuration()

    def l10n_mx_edi_basic_configuration(self):
        self.partner_agrolait.vat = 'MXAAA010101AAA'
        self.company.partner_id.write({
            'vat': 'MXAAA010101AAA',
            'country_id': self.env.ref('base.mx').id,
            'state_id': self.env.ref('base.state_mx_jal').id,
            'street': 'Company Street',
            'street2': 'Company Street 2',
            'street_number': 'Company Internal Number',
            'street_number2': 'Company Internal Number 2',
            'city': 'Company City',
            'zip': '37200',
        })
        self.account_settings.create({
            'l10n_mx_edi_pac': 'finkok',
            'l10n_mx_edi_pac_test_env': True,
            'l10n_mx_edi_pac_username': 'cfdi@vauxoo.com',
            'l10n_mx_edi_pac_password': 'vAux00__',
            'l10n_mx_edi_certificate_ids': [{
                'content': base64.encodestring(self.cert),
                'key': base64.encodestring(self.cert_key),
                'password': self.cert_password,
            }]
        }).execute()

    def test_l10n_mx_edi_invoice_basic(self):
        invoice = self.create_invoice()
        invoice.action_invoice_open()
        self.assertEqual(invoice.state, "open")
        self.assertEqual(invoice.l10n_mx_edi_pac_status, "signed")
        attachments = self.attachments(invoice)
        xml_str = base64.decodestring(attachments[0].datas)
        xml = etree.fromstring(xml_str)
        # TODO: Validate versus expected xml when generated a good xml
        # print etree.tostring(xml, pretty_print=True)

    def test_l10n_mx_edi_invoice_journal_address(self):
        invoice = self.create_invoice()
        invoice.action_invoice_open()
        address = self.partner_agrolait.child_ids[0]
        invoice.journal_id.l10n_mx_address_issued_id = address.id
        self.assertEqual(invoice.state, "open")
        self.assertEqual(invoice.l10n_mx_edi_pac_status, "signed")
        attachments = self.attachments(invoice)
        xml_str = base64.decodestring(attachments[0].datas)
        xml = etree.fromstring(xml_str)
        # TODO: Validate versus expected xml when generated a good xml
        # print etree.tostring(xml, pretty_print=True)
