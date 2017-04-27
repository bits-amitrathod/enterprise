# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrRecruitmentConfigSettings(models.TransientModel):
    _inherit = 'hr.recruitment.config.settings'

    access_token_validity = fields.Integer(string='Default Access Token Validity Duration')

    @api.model
    def get_default_access_token_validity(self, fields):
        access_token_validity = self.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.access_token_validity', default=30)
        return dict(access_token_validity=access_token_validity)

    @api.multi
    def set_default_access_token_validity(self):
        self.env['ir.config_parameter'].sudo().set_param("hr_contract_salary.access_token_validity", self.access_token_validity)
