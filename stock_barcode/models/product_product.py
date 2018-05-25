# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class Product(models.Model):
    _inherit = 'product.product'

    @api.model
    def get_all_products_by_barcode(self):
        products = self.env['product.product'].search_read(
            [('barcode', '!=', None), ('type', '!=', 'service')],
            ['barcode', 'display_name', 'uom_id', 'tracking']
        )
        return {product.pop('barcode'): product for product in products}
