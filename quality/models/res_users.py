# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    group_quality_user = fields.Selection(
        selection=lambda self: self._get_group_selection('quality.module_category_quality'),
        string='Quality', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='quality.module_category_quality',
        help='Officer: The quality user uses the quality process\nManager: The quality manager manages the quality process')
