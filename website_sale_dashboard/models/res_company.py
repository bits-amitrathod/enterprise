# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # dashboard onboarding
    website_sale_dashboard_onboarding_closed = fields.Boolean(
        string="Website sale dashboard onboarding panel closed",
        help="Refers to the website sale dashboard onboarding panel closed state.")
    website_sale_dashboard_onboarding_folded = fields.Boolean(
        string="Website sale dashboard onboarding panel folded",
        help="Refers to the website sale dashboard onboarding panel folded state.")

    @api.model
    def action_toggle_fold_website_sale_dashboard_onboarding(self):
        """ Toggle the website sale dashboard onboarding panel `folded` state. """
        self.env.user.company_id.website_sale_dashboard_onboarding_folded =\
            not self.env.user.company_id.website_sale_dashboard_onboarding_folded

    @api.model
    def action_close_website_sale_dashboard_onboarding(self):
        """ Mark the website sale dashboard onboarding panel as closed. """
        self.env.user.company_id.website_sale_dashboard_onboarding_closed = True
