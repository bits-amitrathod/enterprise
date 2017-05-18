# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleSubscriptionConfigSettings(models.TransientModel):
    _name = 'sale.subscription.config.settings'
    _inherit = 'res.config.settings'

    module_website_subscription = fields.Boolean('Online Subscriptions')
    module_sale_subscription_dashboard = fields.Boolean('Sale Subscription Dashboard')
    module_sale_subscription_asset = fields.Boolean('Deferred revenue management for subscriptions')
    module_account_accountant = fields.Boolean('Accounting and Finance')
