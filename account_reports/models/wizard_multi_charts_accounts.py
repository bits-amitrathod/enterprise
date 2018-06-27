# coding: utf-8
from odoo import api, fields, models, _


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.multi
    def execute(self):
        res = super(WizardMultiChartsAccounts, self).execute()

        # by default, anglo-saxon companies should have totals
        # displayed below sections in their reports
        self.company_id.totals_below_sections = self.company_id.anglo_saxon_accounting

        return res
