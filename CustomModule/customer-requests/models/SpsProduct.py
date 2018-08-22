# -*- coding: utf-8 -*-

from odoo import models, fields, api


# class OdooProduct(models.Model):
#     _inherit = 'product.product'
#     sps_product_ids = fields.One2many('sps.product', 'product_id')


class SpsProductTemplate(models.Model):
    _inherit = 'product.template'
    sku_code = fields.Char(string='SKU Code')


# class SpsProduct(models.Model):
#     _name = 'sps.product'
#     request_ids = fields.One2many('sps.customer.requests', 'product_id')
#     product_id = fields.Many2one('product.product', string='Product', required=True)
#     customer_id = fields.Integer()
#     customer_sku = fields.Char()
#     sps_sku = fields.Char()
#     status = fields.Char()
