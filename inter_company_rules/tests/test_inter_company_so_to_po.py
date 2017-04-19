# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestInterCompanyRulesCommon


class TestInterCompanySaleToPurchase(TestInterCompanyRulesCommon):

    def test_00_inter_company_sale_to_purchase_flow(self):
        """ Create sale order and find related purchase order to related company and compare them """

        # Create sale order for company_A.
        default_get_vals = self.env['sale.order'].default_get(list(self.env['sale.order'].fields_get()))
        default_get_vals.update({
            'company_id': self.company_a.id,
            'warehouse_id': self.company_a.warehouse_id.id,
            'user_id': self.res_users_company_a.id,
            'pricelist_id': 1,
            'partner_id': self.company_b.partner_id.id,
            'partner_invoice_id': self.company_b.partner_id.id,
            'partner_shipping_id': self.company_b.partner_id.id,
        })
        sale_order_cmpa = self.env['sale.order'].new(default_get_vals)
        sale_order_cmpa.onchange_partner_shipping_id()
        sale_order_cmpa.onchange_partner_id()
        sale_order_cmpa.order_line = [(0, 0, {
            'name': 'Service',
            'product_id': self.product_consultant.id,
            'order_id': sale_order_cmpa,
        })]
        sale_order_cmpa.order_line.product_id_change()
        sale_order_cmpa.order_line.price_unit = 450.0
        vals = sale_order_cmpa._convert_to_write(sale_order_cmpa._cache)
        sale_order_cmpa = self.env['sale.order'].create(vals)

        # Confirm Sale order
        sale_order_cmpa.action_confirm()

        # I check that Quotation of purchase order and order line is same as sale order
        purchase_order = self.env['purchase.order'].search([('company_id', '=', self.company_b.id)], limit=1)

        self.assertTrue(purchase_order.state == "draft", "Invoice should be in draft state.")
        self.assertTrue(purchase_order.partner_id == self.company_a.partner_id, "Vendor does not correspond to Company A.")
        self.assertTrue(purchase_order.company_id == self.company_b, "Company is not correspond to purchase order.")
        self.assertTrue(purchase_order.amount_total == 450.0, "Total amount is incorrect.")
        self.assertTrue(purchase_order.order_line[0].product_id == self.product_consultant, "Product in line is incorrect.")
        self.assertTrue(purchase_order.order_line[0].name == 'Service', "Product name is incorrect.")
        self.assertTrue(purchase_order.order_line[0].price_unit == 450, "Price unit is incorrect.")
        self.assertTrue(purchase_order.order_line[0].product_qty == 1, "Product qty is incorrect.")
        self.assertTrue(purchase_order.order_line[0].price_subtotal == 450, "line total is incorrect.")
