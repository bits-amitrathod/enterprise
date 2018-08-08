# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SpsCustomerProductPriority(models.Model):

    _name = 'sps.customer.product.priority'

    product_id = fields.Char()
    customer_id = fields.Integer()
    product_priority = fields.Integer()
    product_threshold = fields.Integer()
    manufacturer = fields.Char()
    cooling_period = fields.Integer()
    auto_allocate = fields.Char()
    length_of_hold = fields.Char()
    expiration_tolarance = fields.Char()
    allow_partial_ordering = fields.Boolean(default=True)
    partial_uom = fields.Char()
    last_purchase_date = fields.Date()
