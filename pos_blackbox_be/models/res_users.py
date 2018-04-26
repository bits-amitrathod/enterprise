# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_minfin_personnel = fields.Boolean(
        'Read-only FDM', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='pos_blackbox_be.group_minfin_personnel')
