# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    show_ocr_option_selection = fields.Selection(related='company_id.show_ocr_option_selection', string='OCR Mode')