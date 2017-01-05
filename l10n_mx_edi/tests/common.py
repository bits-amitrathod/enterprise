# coding: utf-8

from odoo.tests.common import TransactionCase


class InvoiceTransactionCase(TransactionCase):
    def setUp(self):
        super(InvoiceTransactionCase, self).setUp()
        self.invoice_model = self.env['account.invoice']
        self.invoice_line_model = self.env['account.invoice.line']
        self.tax_model = self.env['account.tax']
        self.partner_agrolait = self.env.ref("base.res_partner_2")
        self.product = self.env.ref("product.product_product_3")
        self.company = self.env.user.company_id
        self.account_settings = self.env['account.config.settings']
        self.tax_positive = self.tax_model.create({
            'name': 'IVA16',
            'description': 'IVA',
            'amount_type': 'percent',
            'amount': 16,
        })
        self.tax_negative = self.tax_model.create({
            'name': 'ISR',
            'amount_type': 'percent',
            'amount': -10,
        })
        self.tax_zero = self.tax_model.create({
            'name': 'IVA Exento',
            'description': 'iva',
            'amount_type': 'percent',
            'amount': 0,
        })
        self.product.taxes_id = [self.tax_positive.id, self.tax_negative.id,
                                 self.tax_zero.id]

    def create_invoice(self, inv_type='out_invoice'):
        invoice = self.invoice_model.create({
            'partner_id': self.partner_agrolait.id,
            'type': inv_type,
        })
        self.create_invoice_line(invoice)
        invoice.compute_taxes()
        return invoice

    def create_invoice_line(self, invoice_id):
        invoice_line = self.invoice_line_model.new({
            'product_id': self.product.id,
            'invoice_id': invoice_id,
            'quantity': 1,
        })
        invoice_line._onchange_product_id()
        invoice_line_dict = invoice_line._convert_to_write({
            name: invoice_line[name] for name in invoice_line._cache})
        self.invoice_line_model.create(invoice_line_dict)

    def attachments(self, invoice):
        domain = [
            ('res_id', '=', invoice.id),
            ('res_model', '=', invoice._name),
            ('name', '=', invoice.l10n_mx_edi_cfdi_name)]
        return self.env['ir.attachment'].search(domain)
