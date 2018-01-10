# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests
from .common import TestInterCompanyRulesCommon


@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestInterCompanyInvoice(TestInterCompanyRulesCommon):

    def test_00_inter_company_invoice_flow(self):
        """ Test inter company invoice flow """

        # Enable auto generate invoice in company.
        (self.company_a + self.company_b).write({
            'so_from_po': False,
            'po_from_so': False,
            'auto_generate_invoices': True
        })

        wizard_vals = {
            'chart_template_id': 1,
            'company_id': self.company_a.id,
            'currency_id': self.env.ref('base.EUR').id,
            'transfer_account_id': self.ref("l10n_generic_coa.transfer_account_id"),
            'code_digits': 6,
            'purchase_tax_id': False,
            'bank_account_code_prefix': 'COMP_A',
            'cash_account_code_prefix': 'TANGO',
            'sale_tax_id': False
        }

        # Configure Chart of Account for company_a.
        self.env['wizard.multi.charts.accounts'].create(wizard_vals).execute()

        # Configure Chart of Account for company_b.
        wizard_vals['company_id'] = self.company_b.id
        self.env['wizard.multi.charts.accounts'].create(wizard_vals).execute()

        # Create Expense Account for company_a.
        account_expense_company_a = self.env['account.account'].sudo(self.res_users_company_a).create({
            'name': 'Expenses',
            'code': 'X1000',
            'user_type_id': self.ref('account.data_account_type_expenses'),
            'company_id': self.company_a.id
        })

        # Create customer invoice for company A. (No need to call onchange as all the needed values are specified)
        customer_invoice = self.env['account.invoice'].sudo(self.res_users_company_a).create({
            'company_id': self.company_a.id,
            'partner_id': self.company_b.partner_id.id,
            'currency_id': self.env.ref('base.EUR').id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_consultant.id,
                'price_unit': 450.0,
                'account_id': account_expense_company_a.id,
                'quantity': 1.0,
                'name': 'test'
            })]
        })

        # Check account invoice state should be draft.
        self.assertEquals(customer_invoice.state, 'draft', 'Initially customer invoice should be in the "Draft" state')

        # Validate invoice
        customer_invoice.sudo(self.res_users_company_a).action_invoice_open()

        # Check Invoice status should be open after validate.
        self.assertEquals(customer_invoice.state, 'open', 'Invoice should be in Open state.')

        # I check that the vendor bill is created with proper data.
        supplier_invoice = self.env['account.invoice'].sudo(self.res_users_company_b.id).search([('type', '=', 'in_invoice')], limit=1)

        self.assertTrue(supplier_invoice.invoice_line_ids[0].quantity == 1, "Quantity in invoice line is incorrect.")
        self.assertTrue(supplier_invoice.invoice_line_ids[0].product_id.id == self.product_consultant.id, "Product in line is incorrect.")
        self.assertTrue(supplier_invoice.invoice_line_ids[0].price_unit == 450, "Unit Price in invoice line is incorrect.")
        self.assertTrue(supplier_invoice.invoice_line_ids[0].account_id.company_id.id == self.company_b.id, "Applied account in created invoice line is not relevant to company.")
        self.assertTrue(supplier_invoice.state == "draft", "invoice should be in draft state.")
        self.assertTrue(supplier_invoice.amount_total == 450.0, "Total amount is incorrect.")
        self.assertTrue(supplier_invoice.company_id.id == self.company_b.id, "Applied company in created invoice is incorrect.")
        self.assertTrue(supplier_invoice.account_id.company_id.id == self.company_b.id, "Applied account in created invoice is not relevant to company.")
