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

    filter_date = {'date_from': '', 'date_to': '', 'filter': 'this_year'}
    filter_cash_basis = False
    filter_all_entries = False
    filter_unfold_all = False
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
        select = ',COALESCE(SUM(\"account_move_line\".debit-\"account_move_line\".credit), 0),SUM(\"account_move_line\".debit),SUM(\"account_move_line\".credit)'
        if options.get('cash_basis'):
            select = select.replace('debit', 'debit_cash_basis').replace('credit', 'credit_cash_basis')
        sql = "SELECT \"account_move_line\".partner_id%s FROM %s WHERE %s%s AND \"account_move_line\".partner_id IS NOT NULL GROUP BY \"account_move_line\".partner_id"
        tables, where_clause, where_params = self.env['account.move.line']._query_get([('account_id.internal_type', 'in', account_types)])
        line_clause = line_id and ' AND \"account_move_line\".partner_id = ' + str(line_id) or ''
        query = sql % (select, tables, where_clause, line_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        results = dict([(k[0], {'balance': k[1], 'debit': k[2], 'credit': k[3]}) for k in results])
        return results

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

        #If a default partner is set, we only want to load the line referring to it.
        if context.get('default_partner_id'):
            line_id = context['default_partner_id']

        grouped_partners = self.group_by_partner_id(options, line_id)
        sorted_partners = sorted(grouped_partners, key=lambda p: p.name)
        unfold_all = context.get('print_mode') and not options.get('unfolded_lines') or context.get('default_partner_id')
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
            if 'partner_' + str(partner.id) in options.get('unfolded_lines') or unfold_all:
                progress = 0
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
                    progress = progress + line_debit - line_credit
                    name = []
                    name = '-'.join(
                        line.move_id.name not in ['', '/'] and [line.move_id.name] or [] +
                        line.ref not in ['', '/'] and [line.ref] or [] +
                        line.name not in ['', '/'] and [line.name] or []
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
                    'name': _('Total') + ' ' + partner.name,
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
