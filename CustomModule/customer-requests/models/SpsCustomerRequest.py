# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SpsCustomerRequest(models.Model):

    _name = 'sps.customer.requests'

    document_id = fields.Integer()
    product_id = fields.Integer()
    contact_id = fields.Integer()
    vendor_pricing = fields.Char()
    quantity = fields.Integer()
    required_quantity = fields.Integer()
    frequency_of_refill = fields.Integer()
    threshold = fields.Integer()
    customer_sku = fields.Char()
    sps_sku = fields.Char()
    uom = fields.Char()
    status = fields.Char()
    customer_id = fields.Integer()
