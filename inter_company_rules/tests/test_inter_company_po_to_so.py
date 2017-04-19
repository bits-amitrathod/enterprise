# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestInterCompanyRulesCommon


class TestInterCompanyPurchaseToSale(TestInterCompanyRulesCommon):

    def test_00_inter_company_purchase_to_sale_flow(self):
        """ Create purchase order and find related sale order in another company."""

        # Create purchase order for company_a.
        default_get_vals = self.env['purchase.order'].default_get(list(self.env['purchase.order'].fields_get()))
        default_get_vals.update({
            'partner_id': self.company_b.partner_id.id,
            'company_id': self.company_a.id
        })
        purchase_order_cmpa = self.env['purchase.order'].new(default_get_vals)
        purchase_order_cmpa.onchange_partner_id()
        purchase_order_cmpa.order_line = [(0, 0, {
            'name': 'Service',
            'product_id': self.product_consultant.id,
            'order_id': purchase_order_cmpa,
        })]
        purchase_order_cmpa.order_line.onchange_product_id()
        purchase_order_cmpa.order_line.price_unit = 450.0
        vals = purchase_order_cmpa._convert_to_write(purchase_order_cmpa._cache)
        purchase_order_cmpa = self.env['purchase.order'].create(vals)

        # Confirm Purchase order
        purchase_order_cmpa.button_confirm()

        # Check purchase order state should be purchase.
        self.assertEquals(purchase_order_cmpa.state, 'purchase', 'Purchase order should be in purchase state.')

        # Find related sale order based on client order reference.
        sale_order = self.env['sale.order'].search([('client_order_ref', '=', purchase_order_cmpa.name)], limit=1)

        self.assertTrue(sale_order.state == "draft", "sale order should be in draft state.")
        self.assertTrue(sale_order.partner_id == self.company_a.partner_id, "Vendor does not correspond to Company A.")
        self.assertTrue(sale_order.company_id == self.company_b, "Applied company in created sale order is incorrect.")
        self.assertTrue(sale_order.amount_total == 450.0, "Total amount is incorrect.")
        self.assertTrue(sale_order.order_line[0].product_id == self.product_consultant, "Product in line is incorrect.")
        self.assertTrue(sale_order.order_line[0].name == 'Service', "Product name is incorrect.")
        self.assertTrue(sale_order.order_line[0].product_uom_qty == 1, "Product qty is incorrect.")
        self.assertTrue(sale_order.order_line[0].price_unit == 450, "Unit Price in line is incorrect.")
