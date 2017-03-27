# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _website_product_id_change(self, order_id, product_id, qty=0):
        res = super(SaleOrder, self)._website_product_id_change(order_id, product_id, qty)
        line = self._cart_find_product_line(product_id=product_id)
        if line and line.force_price:
            res['price_unit'] = line.price_unit
            res['product_uom'] = line.product_uom.id
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    force_price = fields.Boolean('Force price', help='Force a specific price, regardless of any coupons or pricelist change', default=False)
