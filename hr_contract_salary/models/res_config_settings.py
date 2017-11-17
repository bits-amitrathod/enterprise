# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    access_token_validity = fields.Integer(string='Default Access Token Validity Duration',
                                           default=30,
                                           config_parameter='hr_contract_salary.access_token_validity')
