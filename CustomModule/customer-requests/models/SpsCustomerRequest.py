# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SpsCustomerRequest(models.Model):

    _name = 'sps.customer.requests'

    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    document_id = fields.Many2one('sps.cust.uploaded.documents', string='Document', required=True)
    product_id = fields.Many2one('sps.product', string='Product', required=False, default=0)

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
    un_mapped_data = fields.Text()
