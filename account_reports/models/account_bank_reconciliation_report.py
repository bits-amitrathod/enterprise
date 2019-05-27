# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools.misc import formatLang


class account_bank_reconciliation_report(models.AbstractModel):
    _name = 'account.bank.reconciliation.report'
    _description = 'Bank reconciliation report'
    _inherit = "account.report"

    filter_date = {'date': '', 'filter': 'today'}

    #used to enumerate the 'layout' lines with a distinct ID
    line_number = 0

    def get_columns_name(self, options):
        return [
            {'name': ''},
            {'name': _("Date")},
            {'name': _("Reference")},
            {'name': _("Amount"), 'class': 'number'},
        ]

    def add_title_line(self, options, title, amount):
        self.line_number += 1
        line_currency = self.env.context.get('line_currency', False)
        return {
            'id': 'line_' + str(self.line_number),
            'name': title,
            'columns': [{'name': v} for v in [options['date']['date'], '', self.format_value(amount, line_currency)]],
            'level': 0,
        }

    def add_subtitle_line(self, title, amount=None):
        self.line_number += 1
        line_currency = self.env.context.get('line_currency', False)
        return {
            'id': 'line_' + str(self.line_number),
            'name': title,
            'columns': [{'name': v} for v in ['', '', amount and self.format_value(amount, line_currency) or '']],
            'level': 1,
        }

    def add_total_line(self, amount):
        self.line_number += 1
        line_currency = self.env.context.get('line_currency', False)
        return {
            'id': 'line_' + str(self.line_number),
            'name': '',
            'columns': [{'name': v} for v in ["", "", self.format_value(amount, line_currency)]],
            'level': 2,
        }

    def add_bank_statement_line(self, line, amount):
        name = line.name
        line_currency = self.env.context.get('line_currency', False)
        return {
            'id': str(line.id),
            #'statement_id': line.statement_id.id,
            #'type': 'bank_statement_id',
            'caret_options': True,
            'name': len(name) >= 85 and name[0:80] + '...' or name,
            'columns': [{'name': v} for v in [line.date, line.ref, self.format_value(amount, line_currency)]],
            'level': 1,
        }

    def print_pdf(self, options):
        options['active_id'] = self.env.context.get('active_id')
        return super(account_bank_reconciliation_report, self).print_pdf(options)

    def print_xlsx(self, options):
        options['active_id'] = self.env.context.get('active_id')
        return super(account_bank_reconciliation_report, self).print_xlsx(options)

    @api.model
    def get_lines(self, options, line_id=None):
        self.env['account.move.line'].check_access_rights('read')

        journal_id = self._context.get('active_id') or options.get('active_id')
        journal = self.env['account.journal'].browse(journal_id)
        lines = []
        if not journal_id:
            return lines
        #Start amount
        use_foreign_currency = \
                journal.currency_id != journal.company_id.currency_id \
                if journal.currency_id else False
        line_currency = journal.currency_id if use_foreign_currency else False
        self = self.with_context(line_currency=line_currency)
        account_ids = (journal.default_debit_account_id + journal.default_credit_account_id).ids
        if account_ids:
            self._cr.execute('''
                SELECT COALESCE(SUM(line.''' + ('amount_currency' if use_foreign_currency else 'balance') + '''), 0) FROM account_move_line line
                WHERE line.account_id IN %s AND line.date <= %s AND line.company_id IN %s
            ''', [
                tuple(account_ids),
                self.env.context['date_to'],
                tuple(self.env.context['company_ids']),
            ])
            start_amount = self._cr.fetchone()[0] or 0
        else:
            start_amount = 0
        lines.append(self.add_title_line(options, _("Current Balance in GL"), start_amount))

        # Un-reconcilied bank statement lines
        aml_query = '''
            SELECT
                line.id                 AS id,
                line.name               AS name,
                line.date               AS date,
                line.ref                AS ref,
                line.amount_currency    AS amount_currency,
                line.balance            AS balance,
                line.payment_id         AS payment_id,
                line.statement_id       AS statement_id,
                invoice.id              AS invoice_id,
                invoice.type            AS invoice_type
            FROM account_move_line line
            LEFT JOIN account_account_type account_type ON account_type.id = line.user_type_id
            LEFT JOIN account_invoice invoice ON invoice.id = line.invoice_id
            LEFT JOIN account_bank_statement_line statement_line ON statement_line.id = line.statement_line_id
            LEFT JOIN account_payment payment ON line.payment_id = payment.id
            LEFT JOIN account_journal journal ON line.journal_id = journal.id
            WHERE CASE
                /* Handles voucher case i.e. the journal of the operation is not bank or cash */
                /* standard case must be the journal on the line */
                WHEN journal.type NOT IN ('cash', 'bank')
                    THEN payment.journal_id
                    ELSE line.journal_id
                END = %s
            AND account_type.type = %s
            AND line.full_reconcile_id  IS NULL
            AND line.date <= %s
            AND line.company_id IN %s
            AND (statement_line.id IS NULL OR statement_line.date > %s)
            ORDER BY line.date DESC, line.id DESC
        '''
        aml_params = [
            journal.id,
            'liquidity',
            self.env.context['date_to'],
            tuple(self.env.context['company_ids']),
            self.env.context['date_to'],
        ]
        # /!\ To forward-port until 12.0 (not included).
        account_bank_reconciliation_start = self._context.get('account_bank_reconciliation_start')
        if account_bank_reconciliation_start:
            aml_query = aml_query.replace('ORDER BY', 'AND line.date > %s ORDER BY')
            aml_params.append(account_bank_reconciliation_start)

        self._cr.execute(aml_query, aml_params)

        move_lines = self._cr.dictfetchall()
        unrec_tot = 0

        if move_lines:
            tmp_lines = []
            for line in move_lines:
                self.line_number += 1
                line_description = line_title = line['ref']
                if line_description and len(line_description) > 83 and not self.env.context.get('print_mode'):
                    line_description = line['ref'][:80] + '...'
                tmp_lines.append({
                    'id': str(line['id']),
                    'name': line['name'],
                    'columns': [
                        {'name': line['date']},
                        {'name': line_description, 'title': line_title, 'class': 'whitespace_print'},
                        {'name': self.format_value(
                            -line['amount_currency'] if use_foreign_currency else -line['balance'],
                            line_currency)
                        },
                    ],
                    'level': 1,
                })
                unrec_tot -= line['amount_currency'] if use_foreign_currency else line['balance']
            if unrec_tot > 0:
                title = _("Plus Unreconciled Payments")
            else:
                title = _("Minus Unreconciled Payments")
            lines.append(self.add_subtitle_line(title))
            lines += tmp_lines
            lines.append(self.add_total_line(unrec_tot))

        # Outstanding plus
        not_reconcile_plus = self.env['account.bank.statement.line'].search(
                [
                    ('statement_id.journal_id', '=', journal_id),
                    ('date', '<=', self.env.context['date_to']),
                    ('journal_entry_ids', '=', False),
                    ('amount', '>', 0),
                    ('company_id', 'in', self.env.context['company_ids'])])
        outstanding_plus_tot = 0
        if not_reconcile_plus:
            lines.append(self.add_subtitle_line(_("Plus Unreconciled Statement Lines")))
            for line in not_reconcile_plus:
                lines.append(self.add_bank_statement_line(line, line.amount))
                outstanding_plus_tot += line.amount
            lines.append(self.add_total_line(outstanding_plus_tot))

        # Outstanding less
        not_reconcile_less = self.env['account.bank.statement.line'].search(
                [
                    ('statement_id.journal_id', '=', journal_id),
                    ('date', '<=', self.env.context['date_to']),
                    ('journal_entry_ids', '=', False),
                    ('amount', '<', 0),
                    ('company_id', 'in', self.env.context['company_ids'])])
        outstanding_less_tot = 0
        if not_reconcile_less:
            lines.append(self.add_subtitle_line(_("Minus Unreconciled Statement Lines")))
            for line in not_reconcile_less:
                lines.append(self.add_bank_statement_line(line, line.amount))
                outstanding_less_tot += line.amount
            lines.append(self.add_total_line(outstanding_less_tot))

        # Final
        computed_stmt_balance = start_amount + outstanding_plus_tot + outstanding_less_tot + unrec_tot
        last_statement = self.env['account.bank.statement'].search(
                [
                    ('journal_id', '=', journal_id),
                    ('date', '<=', self.env.context['date_to']), 
                    ('company_id', 'in', self.env.context['company_ids'])
                ], order="date desc, id desc", limit=1)
        real_last_stmt_balance = last_statement.balance_end
        if computed_stmt_balance != real_last_stmt_balance:
            if real_last_stmt_balance - computed_stmt_balance > 0:
                title = _("Plus Missing Statements")
            else:
                title = _("Minus Missing Statements")
            lines.append(self.add_subtitle_line(title, real_last_stmt_balance - computed_stmt_balance))
        lines.append(self.add_title_line(options, _("Equal Last Statement Balance"), real_last_stmt_balance))
        return lines

    @api.model
    def get_report_name(self):
        journal_id = self._context.get('active_id')
        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            return _("Bank Reconciliation") + ': ' + journal.name
        return _("Bank Reconciliation")
