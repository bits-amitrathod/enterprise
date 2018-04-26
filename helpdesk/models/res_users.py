# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    helpdesk_target_closed = fields.Float(string='Target Tickets to Close')
    helpdesk_target_rating = fields.Float(string='Target Customer Rating')
    helpdesk_target_success = fields.Float(string='Target Success Rate')

    has_group_use_sla = fields.Boolean(
        'Show SLA Policies', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='helpdesk.group_use_sla')

    group_helpdesk_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_helpdesk'),
        string='Helpdesk', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_helpdesk')
