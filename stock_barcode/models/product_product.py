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
        packagings = self.env['product.packaging'].search_read(
            [('barcode', '!=', None), ('product_id', '!=', None)],
            ['barcode', 'product_id', 'qty']
        )
        # for each packaging, grab the corresponding product data
        to_add = []
        for packaging in packagings:
            for product in products:
                if packaging['product_id'] == product['id']:
                    to_add.append(dict(product, **{'qty': packaging['qty']}))
                    break
            # if the product doesn't have a barcode, you need to read it directly in the DB
            to_add.append(dict(packaging, **self.env['product.product'].browse(packaging['product_id'][0]).sudo().read(['display_name', 'uom_id', 'tracking'])[0]))
        return {product.pop('barcode'): product for product in products + to_add}
