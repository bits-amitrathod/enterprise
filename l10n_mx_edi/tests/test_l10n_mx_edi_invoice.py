# coding: utf-8

import base64
import os

from lxml import etree, objectify

from odoo.tools import misc

from . import common


class TestL10nMxEdiInvoice(common.InvoiceTransactionCase):
    def setUp(self):
        super(TestL10nMxEdiInvoice, self).setUp()
        self.cert = misc.file_open(os.path.join(
            'l10n_mx_edi', 'demo', 'pac_credentials', 'certificate.cer')).read()
        self.cert_key = misc.file_open(os.path.join(
            'l10n_mx_edi', 'demo', 'pac_credentials', 'certificate.key')).read()
        self.cert_password = '12345678a'
        self.l10n_mx_edi_basic_configuration()
        self.company_partner = self.env.ref('base.main_partner')

    def l10n_mx_edi_basic_configuration(self):
        self.company.write({
            'currency_id': self.mxn.id,
        })
        self.company.partner_id.write({
            'vat': 'TCM970625MB1',
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

    def test_multi_currency(self):
        invoice = self.create_invoice()
        usd_rate = 20.0

        # -----------------------
        # Testing company.mxn.rate=1 and invoice.usd.rate=1/value
        # -----------------------
        self.set_currency_rates(mxn_rate=1, usd_rate=1/usd_rate)
        values = invoice._l10n_mx_edi_create_cfdi_values()
        self.assertEqual(float(values['rate']), usd_rate)

        # -----------------------
        # Testing company.mxn.rate=value and invoice.usd.rate=1
        # -----------------------
        self.set_currency_rates(mxn_rate=usd_rate, usd_rate=1)
        values = invoice._l10n_mx_edi_create_cfdi_values()
        self.assertEqual(float(values['rate']), usd_rate)

        # -----------------------
        # Testing using MXN currency for invoice and company
        # -----------------------
        invoice.currency_id = self.mxn.id
        values = invoice._l10n_mx_edi_create_cfdi_values()
        self.assertEqual(float(values['rate']), 1)
