# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class HrJob(models.Model):
    _inherit = 'hr.job'

    default_contract_id = fields.Many2one('hr.contract', string="Default Contract for New Employees")
    signature_request_template_id = fields.Many2one('signature.request.template', string="New Contract Document Template")
    contract_update_template_id = fields.Many2one('signature.request.template', string="Contract Update Document Template")

    def open_package_job(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Redirect to the package configurator for a new applicant",
            'target': 'self',
            'url': "/salary_package/job/%s" % (self.id,)
        }
