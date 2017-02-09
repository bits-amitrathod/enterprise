# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    default_print_provider = fields.Many2one('print.provider', string='Default Account', default_model='sale.config.settings')
