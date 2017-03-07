# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    default_print_provider = fields.Many2one('print.provider', string='Default Account')

    @api.model
    def get_default_tax_fields(self, fields):
        default_print_provider = self.env['ir.config_parameter'].sudo().get_param('print_sale.default_print_provider', default=False)
        return dict(default_print_provider=int(default_print_provider))

    @api.multi
    def set_default_tax_fields(self):
        self.env['ir.config_parameter'].sudo().set_param("print_sale.default_print_provider", self.default_print_provider.id)
