# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import models

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _get_open_bills_to_pay_query(self):
        """
        Overriden to take the 'release_to_pay' status into account when getting the
        vendor bills to pay (for other types of journal, its result
        remains unchanged).
        """
        if self.type == 'purchase':
            return ("""SELECT state, amount_total, currency_id AS currency
                   FROM account_invoice
                   WHERE journal_id = %(journal_id)s
                   AND (release_to_pay = 'yes' OR date_due < %(today)s)
                   AND state = 'open';""",
                   {'journal_id':self.id, 'today':datetime.today()})
        return super(AccountJournal, self)._get_open_bills_to_pay_query()

    def _get_bar_graph_select_query(self):
        """
        Overriden to take the 'release_to_pay' status and 'date_due' field into account
        when getting the vendor bills to pay's graph data (for other types of
        journal, its result remains unchanged).
        """
        if self.type == 'purchase':
            return ("""SELECT sum(residual_company_signed) as total, min(date) as aggr_date
                      FROM account_invoice
                      WHERE journal_id = %(journal_id)s
                      AND (release_to_pay = 'yes'
                          OR date_due < %(today)s)
                      AND state = 'open'""",
                      {'journal_id':self.id, 'today':datetime.today()})
        return super(AccountJournal, self)._get_bar_graph_select_query()
