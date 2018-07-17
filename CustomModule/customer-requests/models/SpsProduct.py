# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SpsProduct(models.Model):

    _name = 'sps.product'

    product_name = fields.Char()
    customer_id = fields.Integer()
    product_description = fields.Char()
    multiplier = fields.Integer()
    price = fields.Integer()
    quantity_in_stock = fields.Integer()
    quantity_allocated = fields.Integer()
    customer_sku = fields.Char()
    sps_sku = fields.Char()
    uom = fields.Char()
    status = fields.Char()
