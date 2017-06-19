# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    default_provider_id = fields.Many2one(
        'print.provider', string='Default Print Provider',
        default_model='print.order')
