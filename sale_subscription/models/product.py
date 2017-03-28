# -*- coding: utf-8 -*-
from odoo import models, fields, api


class product_template(models.Model):
    _inherit = "product.template"

    recurring_invoice = fields.Boolean('Can be Subscribed', help='If set, confirming a sales order with this product will create a subscription')
