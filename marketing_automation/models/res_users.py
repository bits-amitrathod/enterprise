# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    group_marketing_automation_user = fields.Selection(
        selection=lambda self: self._get_group_selection('marketing_automation.module_marketing_automation_category'),
        string='Marketing Automation', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='marketing_automation.module_marketing_automation_category')
