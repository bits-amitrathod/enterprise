# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    forecast_uom = fields.Selection([
        ('hour', 'Hours'),
        ('day', 'Days'),
    ], string="Time Unit", related='company_id.forecast_uom', required=True, help="Encode your forecasts in hours or days.")
    forecast_span = fields.Selection([
        ('day', 'By day'),
        ('week', 'By week'),
        ('month', 'By month')
    ], string="Time Span", related='company_id.forecast_span', required=True, help="Encode your forecast in a table displayed by days, weeks or the whole year.")
