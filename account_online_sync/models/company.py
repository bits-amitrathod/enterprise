# -*- coding: utf-8 -*-

from odoo import api, models, fields, _

class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def setting_init_bank_account_action(self):
        """ Setup bar function, overridden to call the online synchronization wizard
        allowing to setup bank account instead of the default wizard used in community.
        If no bank journal exists yet, we create one first."""
        company = self.env.user.company_id

        bank_journal = self.env['account.journal'].search([('company_id','=', company.id), ('type','=','bank')], limit=1)

        if not bank_journal:
            bank_journal = self.env['account.journal'].create({
                'company_id': company.id,
                'type': 'bank',
                'name': _('Bank Journal'),
            })

        return bank_journal.action_choose_institution()