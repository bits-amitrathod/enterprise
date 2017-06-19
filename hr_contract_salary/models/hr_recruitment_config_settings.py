# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrRecruitmentConfigSettings(models.TransientModel):
    _inherit = 'hr.recruitment.config.settings'

    access_token_validity = fields.Integer(string='Default Access Token Validity Duration')

    @api.model
    def get_values(self):
        res = super(HrRecruitmentConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            access_token_validity=params.get_param('hr_contract_salary.access_token_validity', default=30)
        )
        return res

    @api.multi
    def set_values(self):
        super(HrRecruitmentConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("hr_contract_salary.access_token_validity", self.access_token_validity)
