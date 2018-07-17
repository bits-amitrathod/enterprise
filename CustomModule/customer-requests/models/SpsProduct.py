# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SpsProduct(models.Model):

    _name = 'sps.product'

    product_id = fields.Char()
    customer_id = fields.Integer()
    customer_sku = fields.Char()
    sps_sku = fields.Char()
    status = fields.Char()
