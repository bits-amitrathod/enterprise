# coding: utf-8

import base64
import os
import json

from lxml import etree, objectify

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
        xml_expected_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'expected_cfdi.xml')
        xml_expected_f = open(xml_expected_path)
        self.xml_expected = objectify.parse(xml_expected_f).getroot()
        self.payment_method_cash = self.env.ref(
            'l10n_mx_edi.payment_method_efectivo')
        self.account_payment = self.env['res.partner.bank'].create({
            'acc_number': '123456789',
        })

    def l10n_mx_edi_basic_configuration(self):
        self.partner_agrolait.vat = 'MXXXX010101XXX'
        self.company.partner_id.write({
            'vat': 'MXAAA010101AAA',
            'country_id': self.env.ref('base.mx').id,
            'state_id': self.env.ref('base.state_mx_jal').id,
            'street_name': 'Company Street',
            'street2': 'Company Street 2',
            'street_number': 'Company Internal Number',
            'street_number2': 'Company Internal Number 2',
            'l10n_mx_edi_colony': 'Company Colony',
            'l10n_mx_edi_locality': 'Company Locality',
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

    def xml_to_json(self, xml):
        """Receive 1 lxml etree object and return a json string"""
        def recursive_dict(element):
            return (element.tag.split('}')[1],
                    dict(map(recursive_dict, element.getchildren()),
                         **element.attrib))
        return json.dumps(dict([recursive_dict(xml)]), default=str)

    def assertEqualXML(self, xml_real, xml_expected):
        """Receive 2 objectify objects and show a diff assert if exists."""
        xml_expected_str = json.loads(self.xml_to_json(xml_expected))
        xml_real_str = json.loads(self.xml_to_json(xml_real))
        self.maxDiff = None
        self.assertEqual(xml_real_str, xml_expected_str)

    def test_l10n_mx_edi_invoice_basic(self):
        invoice = self.create_invoice()
        invoice.l10n_mx_edi_payment_method_id = self.payment_method_cash.id
        invoice.l10n_mx_edi_partner_bank_id = self.account_payment.id
        invoice.action_invoice_open()
        self.assertEqual(invoice.state, "open")
        self.assertEqual(invoice.l10n_mx_edi_pac_status, "signed")
        attachments = self.attachments(invoice)
        xml_str = base64.decodestring(attachments[0].datas)
        xml = objectify.fromstring(xml_str.encode("UTF-8"))
        xml.remove(xml.Complemento)
        self.xml_expected.attrib['folio'] = invoice.number
        self.xml_expected.attrib['fecha'] = xml.attrib['fecha']
        self.xml_expected.attrib['sello'] = xml.attrib['sello']
        xml_expected = etree.tostring(self.xml_expected, pretty_print=True)
        xml_expected = objectify.fromstring(xml_expected.encode("UTF-8"))
        xml_expected.remove(xml_expected.Complemento)
        xml_expected.Emisor.remove(xml_expected.Emisor.ExpedidoEn)
        self.assertEqualXML(xml, xml_expected)

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
