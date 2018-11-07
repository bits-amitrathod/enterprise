# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields
from odoo.tools.misc import formatLang
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta


class ReportPartnerLedger(models.AbstractModel):
    _inherit = "account.report"
    _name = "account.partner.ledger"
    _description = "Partner Ledger"

    filter_date = {'date_from': '', 'date_to': '', 'filter': 'this_month'}
    filter_cash_basis = False
    filter_all_entries = False
    filter_account_type = [{'id': 'receivable', 'name': _('Receivable'), 'selected': False}, {'id': 'payable', 'name': _('Payable'), 'selected': False}] 
    #TODO add support for partner_id

    def get_templates(self):
        templates = super(ReportPartnerLedger, self).get_templates()
        templates['line_template'] = 'account_reports.line_template_partner_ledger_report'
        templates['main_template'] = 'account_reports.template_partner_ledger_report'
        return templates

    def get_columns_name(self, options):
        return [
            {},
            {'name': _('JRNL')},
            {'name': _('Account')},
            {'name': _('Ref')},
            {'name': _('Matching Number')},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('Balance'), 'class': 'number'},
        ]

    def set_context(self, options):
        ctx = super(ReportPartnerLedger, self).set_context(options)
        ctx['strict_range'] = True
        return ctx

    def do_query(self, options, line_id):
        account_types = [a.get('id') for a in options.get('account_type') if a.get('selected', False)]
        if not account_types:
            account_types = [a.get('id') for a in options.get('account_type')]
        # Create the currency table.
        user_company = self.env.user.company_id
        companies = self.env['res.company'].search([])
        rates_table_entries = []
        for company in companies:
            if company.currency_id == user_company.currency_id:
                rate = 1.0
            else:
                rate = user_company.currency_id.rate / company.currency_id.rate
            rates_table_entries.append((company.id, rate, user_company.currency_id.decimal_places))
        currency_table = ','.join('(%s, %s, %s)' % r for r in rates_table_entries)
        with_currency_table = 'WITH currency_table(company_id, rate, precision) AS (VALUES %s)' % currency_table

        # Sum query
        debit_field = 'debit_cash_basis' if options.get('cash_basis') else 'debit'
        credit_field = 'credit_cash_basis' if options.get('cash_basis') else 'credit'
        balance_field = 'balance_cash_basis' if options.get('cash_basis') else 'balance'
        tables, where_clause, params = self.env['account.move.line']._query_get(
            [('account_id.internal_type', 'in', account_types)])
        query = '''
            SELECT
                \"account_move_line\".partner_id,
                SUM(ROUND(\"account_move_line\".''' + debit_field + ''' * currency_table.rate, currency_table.precision))     AS debit,
                SUM(ROUND(\"account_move_line\".''' + credit_field + ''' * currency_table.rate, currency_table.precision))    AS credit,
                SUM(ROUND(\"account_move_line\".''' + balance_field + ''' * currency_table.rate, currency_table.precision))   AS balance
            FROM %s
            LEFT JOIN currency_table                    ON currency_table.company_id = \"account_move_line\".company_id
            WHERE %s
            AND \"account_move_line\".partner_id IS NOT NULL
            GROUP BY \"account_move_line\".partner_id
        ''' % (tables, where_clause)
        if line_id:
            query = query.replace('WHERE', 'WHERE \"account_move_line\".partner_id = %s AND ')
            params = [str(line_id)] + params
        self._cr.execute(with_currency_table + query, params)
        query_res = self._cr.dictfetchall()
        return dict((res['partner_id'], res) for res in query_res)

    def group_by_partner_id(self, options, line_id):
        partners = {}
        account_types = [a.get('id') for a in options.get('account_type') if a.get('selected', False)]
        if not account_types:
            account_types = [a.get('id') for a in options.get('account_type')]

        date_from = options['date']['date_from']
        results = self.with_context(date_from=False).do_query(options, line_id)
        initial_bal_date_to = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT) + timedelta(days=-1)
        initial_bal_results = self.with_context(date_from=False, date_to=initial_bal_date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)).do_query(options, line_id)

        context = self.env.context
        base_domain = [('date', '<=', context['date_to']), ('company_id', 'in', context['company_ids']), ('account_id.internal_type', 'in', account_types)]
        base_domain.append(('date', '>=', date_from))
        if context['state'] == 'posted':
            base_domain.append(('move_id.state', '=', 'posted'))
        for partner_id, result in results.items():
            domain = list(base_domain)  # copying the base domain
            domain.append(('partner_id', '=', partner_id))
            partner = self.env['res.partner'].browse(partner_id)
            partners[partner] = result
            partners[partner]['initial_bal'] = initial_bal_results.get(partner.id, {'balance': 0, 'debit': 0, 'credit': 0})
            if not context.get('print_mode'):
                #  fetch the 81 first amls. The report only displays the first 80 amls. We will use the 81st to know if there are more than 80 in which case a link to the list view must be displayed.
                partners[partner]['lines'] = self.env['account.move.line'].search(domain, order='date', limit=81)
            else:
                partners[partner]['lines'] = self.env['account.move.line'].search(domain, order='date')
        return partners

    @api.model
    def get_lines(self, options, line_id=None):
        lines = []
        if line_id:
            line_id = line_id.replace('partner_', '')
        context = self.env.context

        grouped_partners = self.group_by_partner_id(options, line_id)
        sorted_partners = sorted(grouped_partners, key=lambda p: p.name)
        unfold_all = context.get('print_mode') and not options.get('unfolded_lines')
        for partner in sorted_partners:
            debit = grouped_partners[partner]['debit']
            credit = grouped_partners[partner]['credit']
            balance = grouped_partners[partner]['balance']
            lines.append({
                'id': 'partner_' + str(partner.id),
                'name': partner.name,
                'columns': [{'name': v} for v in [self.format_value(debit), self.format_value(credit), self.format_value(balance)]],
                'level': 2,
                'trust': partner.trust,
                'unfoldable': True,
                'unfolded': 'partner_' + str(partner.id) in options.get('unfolded_lines') or unfold_all,
                'colspan': 5,
            })
            used_currency = company_id.currency_id
            if 'partner_' + str(partner.id) in options.get('unfolded_lines') or unfold_all:
                progress = grouped_partners[partner]['initial_bal']['balance']
                domain_lines = []
                amls = grouped_partners[partner]['lines']
                too_many = False
                if len(amls) > 80 and not context.get('print_mode'):
                    amls = amls[-80:]
                    too_many = True
                for line in amls:
                    if options.get('cash_basis'):
                        line_debit = line.debit_cash_basis
                        line_credit = line.credit_cash_basis
                    else:
                        line_debit = line.debit
                        line_credit = line.credit
                    line_currency = line.company_id.currency_id.with_context(date=amls.env.context.get('date') or fields.Date.today())
                    line_debit = line_currency.compute(line_debit, used_currency)
                    line_credit = line_currency.compute(line_credit, used_currency)
                    progress = progress + line_debit - line_credit
                    name = []
                    name = '-'.join(
                        (line.move_id.name not in ['', '/'] and [line.move_id.name] or []) +
                        (line.ref not in ['', '/', False] and [line.ref] or []) +
                        ([line.name] if line.name and line.name not in ['', '/'] else [])
                    )
                    if len(name) > 35 and not self.env.context.get('no_format'):
                        name = name[:32] + "..."
                    caret_type = 'account.move'
                    if line.invoice_id:
                        caret_type = 'account.invoice.in' if line.invoice_id.type in ('in_refund', 'in_invoice') else 'account.invoice.out'
                    elif line.payment_id:
                        caret_type = 'account.payment'
                    domain_lines.append({
                        'id': line.id,
                        'parent_id': 'partner_' + str(partner.id),
                        'name': line.date,
                        'columns': [{'name': v} for v in [line.journal_id.code, line.account_id.code, name, line.full_reconcile_id.name,
                                    line_debit != 0 and self.format_value(line_debit) or '',
                                    line_credit != 0 and self.format_value(line_credit) or '',
                                    self.format_value(progress)]],
                        'caret_options': caret_type,
                        'level': 1,
                    })
                initial_debit = grouped_partners[partner]['initial_bal']['debit']
                initial_credit = grouped_partners[partner]['initial_bal']['credit']
                initial_balance = grouped_partners[partner]['initial_bal']['balance']
                domain_lines[:0] = [{
                    'id': 'initial_balance_' + str(partner.id),
                    'class': 'o_account_reports_initial_balance',
                    'parent_id': 'partner_' + str(partner.id),
                    'name': _('Initial Balance'),
                    'columns': [{'name': v} for v in ['', '', '', '', self.format_value(initial_debit), self.format_value(initial_credit), self.format_value(initial_balance)]],
                }]
                domain_lines.append({
                    'id': 'total_' + str(partner.id),
                    'parent_id': 'partner_' + str(partner.id),
                    'class': 'o_account_reports_domain_total',
                    'name': _('Total') + ' ' + (partner.name or ''),
                    'columns': [{'name': v} for v in ['', '', '', '', self.format_value(debit), self.format_value(credit), self.format_value(balance)]],
                })
                if too_many:
                    domain_lines.append({
                        'id': 'too_many_' + str(partner.id),
                        'parent_id': 'partner_' + str(partner.id),
                        'action': 'view_too_many',
                        'action_id': 'partner,%s' % (partner.id,),
                        'name': _('There are more than 80 items in this list, click here to see all of them'),
                        'colspan': 7,
                        'columns': [{}],
                    })
                lines += domain_lines
        return lines

    @api.model
    def get_report_name(self):
        return _('Partner Ledger')
