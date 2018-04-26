# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    group_website_calendar_user = fields.Selection(
        selection=lambda self: self._get_group_selection('website_calendar.module_category_calendar'),
        string='Appointments', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='website_calendar.module_category_calendar')
