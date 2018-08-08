# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SpsCustomerTemplateMapper(models.Model):

    _name = 'sps.template.mapper'

    customer_sku = fields.Selection((('choice1', 'ABT'), ('choice2', 'KPN'), ('choice3', 'FREE Courier')), string='SKU')
    required_quantity = fields.Selection((('choice1', 'ABT'), ('choice2', 'KPN'), ('choice3', 'FREE Courier')), string='Required Quantity')
    quantity = fields.Selection((('choice1', 'ABT'), ('choice2', 'KPN'), ('choice3', 'FREE Courier')), string='Stock')
    frequency_of_refill = fields.Selection((('choice1', 'ABT'), ('choice2', 'KPN'), ('choice3', 'FREE Courier')), string='Frequency of Refill')
    uom = fields.Selection((('choice1', 'ABT'), ('choice2', 'KPN'), ('choice3', 'FREE Courier')), string='Unit Of Mesaurement')
