# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    group_sale_subscription_user = fields.Selection(
        selection=lambda self: self._get_group_selection('sale_subscription.module_category_subscription_management'),
        string='Subscriptions', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='sale_subscription.module_category_subscription_management',
        help='group_sale_subscription_view: The user will have read access to subscriptions.\ngroup_sale_subscription_manager: The user will have write access to Subscriptions.')
