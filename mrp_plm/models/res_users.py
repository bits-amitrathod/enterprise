# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    group_mrp_plm_user = fields.Selection(
        selection=lambda self: self._get_group_selection('mrp_plm.module_category_plm'),
        string='PLM', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='mrp_plm.module_category_plm',
        help='group_plm_user: The PLM user uses products lifecycle management\ngroup_plm_manager: The PLM manager manages products lifecycle management')
