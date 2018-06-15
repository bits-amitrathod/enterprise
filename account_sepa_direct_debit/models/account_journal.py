# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def get_batch_payment_methods_list(self):
        """ Overridden from account_batch_payment to include SDD payment method
        """
        rslt = super(AccountJournal, self).get_batch_payment_methods_list()
        rslt.append('sdd')
        return rslt