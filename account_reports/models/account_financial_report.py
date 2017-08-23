# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import copy
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.tools.misc import formatLang
from odoo.tools import float_is_zero, ustr
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo.osv import expression


class ReportAccountFinancialReport(models.Model):
    _name = "account.financial.html.report"
    _description = "Account Report"
    _inherit = "account.report"

    name = fields.Char(translate=True)
    debit_credit = fields.Boolean('Show Credit and Debit Columns')
    line_ids = fields.One2many('account.financial.html.report.line', 'financial_report_id', string='Lines')
    date_range = fields.Boolean('Based on date ranges', default=True, help='specify if the report use date_range or single date')
    comparison = fields.Boolean('Allow comparison', default=True, help='display the comparison filter')
    cash_basis = fields.Boolean('Use cash basis', help='if true, report will always use cash basis, if false, user can choose from filter inside the report')
    analytic = fields.Boolean('Allow analytic filter', help='display the analytic filter')
    unfold_all_filter = fields.Boolean('Show unfold all filter', help='display the unfold all options in report')
    company_id = fields.Many2one('res.company', string='Company')
    menuitem_created = fields.Boolean("Menu Has Been Created", default=False)
    parent_id = fields.Many2one('ir.ui.menu')
    tax_report = fields.Boolean('Tax Report', help="Set to True to automatically filter out journal items that have the boolean field 'tax_exigible' set to False")

    def get_columns_name(self, options):
        columns = [{'name': ''}]
        if self.debit_credit and not options.get('comparison', {}).get('periods', False):
            columns += [{'name': _('Debit'), 'class': 'number'}, {'name': _('Credit'), 'class': 'number'}]
        dt_to = options['date'].get('date_to') or options['date'].get('date')
        columns += [{'name': self.format_date(dt_to, options['date'].get('date_from', False), options), 'class': 'number'}]
        if options.get('comparison') and options['comparison'].get('periods'):
            for period in options['comparison']['periods']:
                columns += [{'name': period.get('string'), 'class': 'number'}]
            if options['comparison'].get('number_period') == 1:
                columns += [{'name': '%', 'class': 'number'}]
        return columns

    @api.model
    def get_options(self, previous_options=None):
        if self.date_range:
            self.filter_date = {'date_from': '', 'date_to': '', 'filter': 'this_year'}
            if self.comparison:
                self.filter_comparison = {'date_from': '', 'date_to': '', 'filter': 'no_comparison', 'number_period': 1}
        else:
            self.filter_date = {'date': '', 'filter': 'today'}
            if self.comparison:
                self.filter_comparison = {'date': '', 'filter': 'no_comparison', 'number_period': 1}
        self.filter_cash_basis = False
        if self.cash_basis:
            self.filter_cash_basis = None
        if self.unfold_all_filter:
            self.filter_unfold_all = False
        self.filter_all_entries = False
        self.filter_analytic = True if self.analytic else None
        return super(ReportAccountFinancialReport, self).get_options(previous_options)

    def create_action_and_menu(self, parent_id):
        # create action and menu with corresponding external ids, in order to
        # remove those entries when deinstalling the corresponding module
        module = self._context.get('install_mode_data', {}).get('module', 'account_reports')
        IMD = self.env['ir.model.data']
        action_vals = {
            'name': self.get_report_name(),
            'tag': 'account_report',
            'context': {
                'model': 'account.financial.html.report',
                'id': self.id,
            },
        }
        action_id = IMD._update('ir.actions.client', module, action_vals,
                                'account_financial_html_report_action_' + str(self.id))
        menu_vals = {
            'name': self.get_report_name(),
            'parent_id': parent_id or IMD.xmlid_to_res_id('account.menu_finance_reports'),
            'action': 'ir.actions.client,%s' % (action_id,),
        }
        IMD._update('ir.ui.menu', module, menu_vals,
                    'account_financial_html_report_menu_' + str(self.id))
        self.write({'menuitem_created': True})

    @api.model
    def create(self, vals):
        parent_id = vals.pop('parent_id', False)
        res = super(ReportAccountFinancialReport, self).create(vals)
        res.create_action_and_menu(parent_id)
        return res

    @api.multi
    def write(self, vals):
        parent_id = vals.pop('parent_id', False)
        res = super(ReportAccountFinancialReport, self).write(vals)
        if parent_id:
            # this keeps external ids "alive" when upgrading the module
            for report in self:
                report.create_action_and_menu(parent_id)
        return res

    @api.multi
    def unlink(self):
        for report in self:
            default_parent_id = self.env['ir.model.data'].xmlid_to_res_id('account.menu_finance_reports')
            menu = self.env['ir.ui.menu'].search([('parent_id', '=', default_parent_id), ('name', '=', report.name)])
            if menu:
                menu.action.unlink()
                menu.unlink()
        return super(ReportAccountFinancialReport, self).unlink()

    @api.multi
    def get_lines(self, options, line_id=None):
        line_obj = self.line_ids
        if line_id:
            line_obj = self.env['account.financial.html.report.line'].search([('id', '=', line_id)])
        if options.get('comparison') and options.get('comparison').get('periods'):
            line_obj = line_obj.with_context(periods=options['comparison']['periods'])
        used_currency = self.env.user.company_id.currency_id.with_context(company_id=self.env.user.company_id.id)
        currency_table = {}
        for company in self.env['res.company'].search([]):
            if company.currency_id != used_currency:
                currency_table[company.currency_id.id] = used_currency.rate / company.currency_id.rate
        linesDicts = [{} for _ in range(0, len(options.get('comparison', {}).get('periods', [])) + 2)]
        res = line_obj.with_context(
            cash_basis=options.get('cash_basis') or self.cash_basis,
        ).get_lines(self, currency_table, options, linesDicts)
        return res

    def get_report_name(self):
        return self.name


class AccountFinancialReportLine(models.Model):
    _name = "account.financial.html.report.line"
    _description = "Account Report Line"
    _order = "sequence"

    name = fields.Char('Section Name', translate=True)
    code = fields.Char('Code')
    financial_report_id = fields.Many2one('account.financial.html.report', 'Financial Report')
    parent_id = fields.Many2one('account.financial.html.report.line', string='Parent')
    children_ids = fields.One2many('account.financial.html.report.line', 'parent_id', string='Children')
    sequence = fields.Integer()

    domain = fields.Char(default=None)
    formulas = fields.Char()
    groupby = fields.Char("Group by", default=False)
    figure_type = fields.Selection([('float', 'Float'), ('percents', 'Percents'), ('no_unit', 'No Unit')],
                                   'Type', default='float', required=True)
    green_on_positive = fields.Boolean('Is growth good when positive', default=True)
    level = fields.Integer(required=True)
    special_date_changer = fields.Selection([('from_beginning', 'From the beginning'), ('to_beginning_of_period', 'At the beginning of the period'), ('normal', 'Use given dates'), ('strict_range', 'Force given dates for all accounts and account types')], default='normal')
    show_domain = fields.Selection([('always', 'Always'), ('never', 'Never'), ('foldable', 'Foldable')], default='foldable')
    hide_if_zero = fields.Boolean(default=False)
    action_id = fields.Many2one('ir.actions.actions')

    _sql_constraints = [
        ('code_uniq', 'unique (code)', "A report line with the same code already exists."),
    ]

    @api.constrains('code')
    def _code_constrains(self):
        if self.code and self.code.strip().lower() in __builtins__.keys():
            raise ValidationError('The code "%s" is invalid on line with name "%s"' % (self.code, self.name))

    def _query_get_select_sum(self, currency_table):
        """ Little function to help building the SELECT statement when computing the report lines.

            @param currency_table: dictionary containing the foreign currencies (key) and their factor (value)
                compared to the current user's company currency
            @returns: the string and parameters to use for the SELECT
        """
        extra_params = []
        select = '''
            COALESCE(SUM(\"account_move_line\".balance), 0) AS balance,
            COALESCE(SUM(\"account_move_line\".amount_residual), 0) AS amount_residual,
            COALESCE(SUM(\"account_move_line\".debit), 0) AS debit,
            COALESCE(SUM(\"account_move_line\".credit), 0) AS credit
        '''
        if currency_table:
            select = 'COALESCE(SUM(CASE '
            for currency_id, rate in currency_table.items():
                extra_params += [currency_id, rate]
                select += 'WHEN \"account_move_line\".company_currency_id = %s THEN \"account_move_line\".balance * %s '
            select += 'ELSE \"account_move_line\".balance END), 0) AS balance, COALESCE(SUM(CASE '
            for currency_id, rate in currency_table.items():
                extra_params += [currency_id, rate]
                select += 'WHEN \"account_move_line\".company_currency_id = %s THEN \"account_move_line\".amount_residual * %s '
            select += 'ELSE \"account_move_line\".amount_residual END), 0) AS amount_residual, COALESCE(SUM(CASE '
            for currency_id, rate in currency_table.items():
                extra_params += [currency_id, rate]
                select += 'WHEN \"account_move_line\".company_currency_id = %s THEN \"account_move_line\".debit * %s '
            select += 'ELSE \"account_move_line\".debit END), 0) AS debit, COALESCE(SUM(CASE '
            for currency_id, rate in currency_table.items():
                extra_params += [currency_id, rate]
                select += 'WHEN \"account_move_line\".company_currency_id = %s THEN \"account_move_line\".credit * %s '
            select += 'ELSE \"account_move_line\".credit END), 0) AS credit'

        if self.env.context.get('cash_basis'):
            for field in ['debit', 'credit', 'balance']:
                #replace the columns selected but not the final column name (... AS <field>)
                number_of_occurence = len(select.split(field)) - 1
                select = select.replace(field, field + '_cash_basis', number_of_occurence - 1)
        return select, extra_params

    def _get_with_statement(self, financial_report):
        """ This function allow to define a WITH statement as prologue to the usual queries returned by query_get().
            It is useful if you need to shadow a table entirely and let the query_get work normally although you're
            fetching rows from your temporary table (built in the WITH statement) instead of the regular tables.

            @returns: the WITH statement to prepend to the sql query and the parameters used in that WITH statement
            @rtype: tuple(char, list)
        """
        sql = ''
        params = []

        #Cash basis option
        #-----------------
        #In cash basis, we need to show amount on income/expense accounts, but only when they're paid AND under the payment date in the reporting, so
        #we have to make a complex query to join aml from the invoice (for the account), aml from the payments (for the date) and partial reconciliation
        #(for the reconciled amount). This is True also for the cash flow statement except for lines 'CASHSTART' and 'CASHEND' because those have to be
        #computed on the normal account_move_line table).
        if self.code not in ('CASHSTART', 'CASHEND') \
          and (financial_report == self.env.ref('account_reports.account_financial_report_cashsummary0') or self.env.context.get('cash_basis')):
            user_types = self.env['account.account.type'].search([('type', 'in', ('receivable', 'payable'))])
            if not user_types:
                return sql, params
            #we use query_get() to filter out unrelevant journal items to have a shadowed table as small as possible
            tables, where_clause, where_params = self.env['account.move.line']._query_get()
            sql = """WITH account_move_line AS (
              SELECT \"account_move_line\".id, \"account_move_line\".date, \"account_move_line\".name, \"account_move_line\".debit_cash_basis, \"account_move_line\".credit_cash_basis, \"account_move_line\".move_id, \"account_move_line\".account_id, \"account_move_line\".journal_id, \"account_move_line\".balance_cash_basis, \"account_move_line\".amount_residual, \"account_move_line\".partner_id, \"account_move_line\".reconciled, \"account_move_line\".company_id, \"account_move_line\".company_currency_id, \"account_move_line\".amount_currency, \"account_move_line\".balance, \"account_move_line\".user_type_id, \"account_move_line\".tax_line_id, \"account_move_line\".invoice_id, \"account_move_line\".credit, \"account_move_line\".tax_exigible, \"account_move_line\".debit, \"account_move_line\".analytic_account_id
               FROM """ + tables + """
               WHERE (\"account_move_line\".journal_id IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                 OR \"account_move_line\".move_id NOT IN (SELECT DISTINCT move_id FROM account_move_line WHERE user_type_id IN %s))
                 AND """ + where_clause + """
              UNION ALL
              (
               WITH payment_table AS (
                 SELECT aml.move_id, \"account_move_line\".date, CASE WHEN aml.balance = 0 THEN 0 ELSE part.amount / ABS(aml.balance) END as matched_percentage
                   FROM account_partial_reconcile part LEFT JOIN account_move_line aml ON aml.id = part.debit_move_id, """ + tables + """
                   WHERE part.credit_move_id = "account_move_line".id
                    AND "account_move_line".user_type_id IN %s
                    AND """ + where_clause + """
                 UNION ALL
                 SELECT aml.move_id, \"account_move_line\".date, CASE WHEN aml.balance = 0 THEN 0 ELSE part.amount / ABS(aml.balance) END as matched_percentage
                   FROM account_partial_reconcile part LEFT JOIN account_move_line aml ON aml.id = part.credit_move_id, """ + tables + """
                   WHERE part.debit_move_id = "account_move_line".id
                    AND "account_move_line".user_type_id IN %s
                    AND """ + where_clause + """
               )
               SELECT aml.id, ref.date, aml.name,
                 CASE WHEN aml.debit > 0 THEN ref.matched_percentage * aml.debit ELSE 0 END AS debit_cash_basis,
                 CASE WHEN aml.credit > 0 THEN ref.matched_percentage * aml.credit ELSE 0 END AS credit_cash_basis,
                 aml.move_id, aml.account_id, aml.journal_id,
                 ref.matched_percentage * aml.balance AS balance_cash_basis,
                 aml.amount_residual, aml.partner_id, aml.reconciled, aml.company_id, aml.company_currency_id, aml.amount_currency, aml.balance, aml.user_type_id, aml.tax_line_id, aml.invoice_id, aml.credit, aml.tax_exigible, aml.debit, aml.analytic_account_id
                FROM account_move_line aml
                RIGHT JOIN payment_table ref ON aml.move_id = ref.move_id
                WHERE journal_id NOT IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                  AND aml.move_id IN (SELECT DISTINCT move_id FROM account_move_line WHERE user_type_id IN %s)
              )
            ) """ 
            params = [tuple(user_types.ids)] + where_params + [tuple(user_types.ids)] + where_params + [tuple(user_types.ids)] + where_params + [tuple(user_types.ids)]
        return sql, params

    def _compute_line(self, currency_table, financial_report, group_by=None, domain=[]):
        """ Computes the sum that appeas on report lines when they aren't unfolded. It is using _query_get() function
            of account.move.line which is based on the context, and an additional domain (the field domain on the report
            line) to build the query that will be used.

            @param currency_table: dictionary containing the foreign currencies (key) and their factor (value)
                compared to the current user's company currency
            @param financial_report: browse_record of the financial report we are willing to compute the lines for
            @param group_by: used in case of conditionnal sums on the report line
            @param domain: domain on the report line to consider in the query_get() call

            @returns : a dictionnary that has for each aml in the domain a dictionnary of the values of the fields
        """
        domain = domain and safe_eval(ustr(domain))
        for index, condition in enumerate(domain):
            if condition[0].startswith('tax_ids.'):
                new_condition = (condition[0].partition('.')[2], condition[1], condition[2])
                taxes = self.env['account.tax'].with_context(active_test=False).search([new_condition])
                domain[index] = ('tax_ids', 'in', taxes.ids)
        tables, where_clause, where_params = self.env['account.move.line']._query_get(domain=domain)
        if financial_report.tax_report:
            where_clause += ''' AND "account_move_line".tax_exigible = 't' '''

        line = self
        financial_report = False

        while(not financial_report):
            financial_report = line.financial_report_id
            if not line.parent_id:
                break
            line = line.parent_id

        sql, params = self._get_with_statement(financial_report)

        select, select_params = self._query_get_select_sum(currency_table)
        where_params = params + select_params + where_params

        if (self.env.context.get('sum_if_pos') or self.env.context.get('sum_if_neg')) and group_by:
            sql = sql + "SELECT account_move_line." + group_by + " as " + group_by + "," + select + " FROM " + tables + " WHERE " + where_clause + " GROUP BY account_move_line." + group_by
            self.env.cr.execute(sql, where_params)
            res = {'balance': 0, 'debit': 0, 'credit': 0, 'amount_residual': 0}
            for row in self.env.cr.dictfetchall():
                if (row['balance'] > 0 and self.env.context.get('sum_if_pos')) or (row['balance'] < 0 and self.env.context.get('sum_if_neg')):
                    for field in ['debit', 'credit', 'balance', 'amount_residual']:
                        res[field] += row[field]
            res['currency_id'] = self.env.user.company_id.currency_id.id
            return res

        sql = sql + "SELECT " + select + " FROM " + tables + " WHERE " + where_clause
        self.env.cr.execute(sql, where_params)
        results = self.env.cr.dictfetchall()[0]
        results['currency_id'] = self.env.user.company_id.currency_id.id
        return results

    @api.multi
    def report_move_lines_action(self):
        domain = safe_eval(self.domain)
        if 'date_from' in self.env.context.get('context', {}):
            if self.env.context['context'].get('date_from'):
                domain = expression.AND([domain, [('date', '>=', self.env.context['context']['date_from'])]])
            if self.env.context['context'].get('date_to'):
                domain = expression.AND([domain, [('date', '<=', self.env.context['context']['date_to'])]])
            if self.env.context['context'].get('state', 'all') == 'posted':
                domain = expression.AND([domain, [('move_id.state', '=', 'posted')]])
            if self.env.context['context'].get('company_ids'):
                domain = expression.AND([domain, [('company_id', 'in', self.env.context['context']['company_ids'])]])
        return {'type': 'ir.actions.act_window',
                'name': 'Journal Items (%s)' % self.name,
                'res_model': 'account.move.line',
                'view_mode': 'tree,form',
                'domain': domain,
                }

    @api.one
    @api.constrains('groupby')
    def _check_same_journal(self):
        if self.groupby and self.groupby not in self.env['account.move.line']:
            raise ValidationError("Groupby should be a journal item field")

    def _get_sum(self, currency_table, financial_report, field_names=None):
        ''' Returns the sum of the amls in the domain '''
        if not field_names:
            field_names = ['debit', 'credit', 'balance', 'amount_residual']
        res = dict((fn, 0.0) for fn in field_names)
        if self.domain:
            strict_range = self.special_date_changer == 'strict_range'
            period_from = self._context['date_from']
            period_to = self._context['date_to']
            if self.special_date_changer == 'from_beginning':
                period_from = False
            if self.special_date_changer == 'to_beginning_of_period' and self._context.get('date_from'):
                date_tmp = datetime.strptime(self._context['date_from'], "%Y-%m-%d") - relativedelta(days=1)
                period_to = date_tmp.strftime('%Y-%m-%d')
                period_from = False

            res = self.with_context(strict_range=strict_range, date_from=period_from, date_to=period_to)._compute_line(currency_table, financial_report, group_by=self.groupby, domain=self.domain)
        return res

    @api.one
    def get_balance(self, linesDict, currency_table, financial_report, field_names=None):
        if not field_names:
            field_names = ['debit', 'credit', 'balance']
        res = dict((fn, 0.0) for fn in field_names)
        c = FormulaContext(self.env['account.financial.html.report.line'], linesDict, currency_table, financial_report, self)
        if self.formulas:
            for f in self.formulas.split(';'):
                [field, formula] = f.split('=')
                field = field.strip()
                if field in field_names:
                    try:
                        res[field] = safe_eval(formula, c, nocopy=True)
                    except ValueError as err:
                        if 'division by zero' in err.args[0]:
                            res[field] = 0
                        else:
                            raise err
        return res

    def _format(self, value):
        if self.env.context.get('no_format'):
            return value
        if self.figure_type == 'float':
            currency_id = self.env.user.company_id.currency_id
            if currency_id.is_zero(value['name']):
                # don't print -0.0 in reports
                value['name'] = abs(value['name'])
            value['name'] = formatLang(self.env, value['name'], currency_obj=currency_id)
            return value
        if self.figure_type == 'percents':
            value['name'] = str(round(value['name'] * 100, 1)) + '%'
            return value
        value['name'] = round(value['name'], 1)
        return value

    def _get_gb_name(self, gb_id):
        if self.groupby and self.env['account.move.line']._fields[self.groupby].relational:
            relation = self.env['account.move.line']._fields[self.groupby].comodel_name
            gb = self.env[relation].browse(gb_id)
            return gb.name_get()[0][1] if gb and gb.exists() else _('Undefined')
        return gb_id

    def _build_cmp(self, balance, comp):
        if comp != 0:
            res = round((balance - comp) / comp * 100, 1)
            if (res > 0) != self.green_on_positive:
                return {'name': str(res) + '%', 'class': 'number color-red'}
            else:
                return {'name': str(res) + '%', 'class': 'number color-green'}
        else:
            return {'name': _('n/a')}

    def _split_formulas(self):
        result = {}
        if self.formulas:
            for f in self.formulas.split(';'):
                [column, formula] = f.split('=')
                column = column.strip()
                result.update({column: formula})
        return result

    def _eval_formula(self, financial_report, debit_credit, currency_table, linesDict):
        debit_credit = debit_credit and financial_report.debit_credit
        formulas = self._split_formulas()
        if self.code and self.code in linesDict:
            res = linesDict[self.code]
        else:
            res = FormulaLine(self, currency_table, financial_report, linesDict=linesDict)
        vals = {}
        vals['balance'] = res.balance
        if debit_credit:
            vals['credit'] = res.credit
            vals['debit'] = res.debit

        results = {}
        if self.domain and self.groupby and self.show_domain != 'never':
            aml_obj = self.env['account.move.line']
            tables, where_clause, where_params = aml_obj._query_get(domain=self.domain)
            sql, params = self._get_with_statement(financial_report)
            if financial_report.tax_report:
                where_clause += ''' AND "account_move_line".tax_exigible = 't' '''

            groupby = self.groupby or 'id'
            if groupby not in self.env['account.move.line']:
                raise ValueError('Groupby should be a field from account.move.line')
            select, select_params = self._query_get_select_sum(currency_table)
            params += select_params
            sql = sql + "SELECT \"account_move_line\"." + groupby + ", " + select + " FROM " + tables + " WHERE " + where_clause + " GROUP BY \"account_move_line\"." + groupby

            params += where_params
            self.env.cr.execute(sql, params)
            results = self.env.cr.fetchall()
            results = dict([(k[0], {'balance': k[1], 'amount_residual': k[2], 'debit': k[3], 'credit': k[4]}) for k in results])
            c = FormulaContext(self.env['account.financial.html.report.line'], linesDict, currency_table, financial_report, only_sum=True)
            if formulas:
                for key in results:
                    c['sum'] = FormulaLine(results[key], currency_table, financial_report, type='not_computed')
                    c['sum_if_pos'] = FormulaLine(results[key]['balance'] >= 0.0 and results[key] or {'balance': 0.0}, currency_table, financial_report, type='not_computed')
                    c['sum_if_neg'] = FormulaLine(results[key]['balance'] <= 0.0 and results[key] or {'balance': 0.0}, currency_table, financial_report, type='not_computed')
                    for col, formula in formulas.items():
                        if col in results[key]:
                            results[key][col] = safe_eval(formula, c, nocopy=True)
            to_del = []
            for key in results:
                if self.env.user.company_id.currency_id.is_zero(results[key]['balance']):
                    to_del.append(key)
            for key in to_del:
                del results[key]

        results.update({'line': vals})
        return results

    def _put_columns_together(self, data, domain_ids):
        res = dict((domain_id, []) for domain_id in domain_ids)
        for period in data:
            debit_credit = False
            if 'debit' in period['line']:
                debit_credit = True
            for domain_id in domain_ids:
                if debit_credit:
                    res[domain_id].append(period.get(domain_id, {'debit': 0})['debit'])
                    res[domain_id].append(period.get(domain_id, {'credit': 0})['credit'])
                res[domain_id].append(period.get(domain_id, {'balance': 0})['balance'])
        return res

    def _divide_line(self, line):
        line1 = {
            'id': line['id'],
            'name': line['name'],
            'level': line['level'],
            'columns': [{'name': ''}] * len(line['columns']),
            'unfoldable': line['unfoldable'],
            'unfolded': line['unfolded'],
        }
        line2 = {
            'id': line['id'],
            'name': _('Total') + ' ' + line['name'],
            'class': 'total',
            'level': line['level'] + 1,
            'columns': line['columns'],
        }
        return [line1, line2]

    @api.multi
    def get_lines(self, financial_report, currency_table, options, linesDicts):
        final_result_table = []
        comparison_table = [options.get('date')]
        comparison_table += options.get('comparison') and options['comparison'].get('periods', []) or []
        currency_precision = self.env.user.company_id.currency_id.rounding
        # build comparison table
        for line in self:
            res = []
            debit_credit = len(comparison_table) == 1
            domain_ids = {'line'}
            k = 0
            for period in comparison_table:
                period_from = period.get('date_from', False)
                period_to = period.get('date_to', False) or period.get('date', False)
                strict_range = False
                if line.special_date_changer == 'from_beginning':
                    period_from = False
                if line.special_date_changer == 'to_beginning_of_period':
                    date_tmp = datetime.strptime(period_from, "%Y-%m-%d") - relativedelta(days=1)
                    period_to = date_tmp.strftime('%Y-%m-%d')
                    period_from = False
                if line.special_date_changer == 'strict_range':
                    strict_range = True
                r = line.with_context(date_from=period_from, date_to=period_to, strict_range=strict_range)._eval_formula(financial_report, debit_credit, currency_table, linesDicts[k])
                debit_credit = False
                res.append(r)
                domain_ids.update(set(r.keys()))
                k += 1
            res = self._put_columns_together(res, domain_ids)
            if line.hide_if_zero and all([float_is_zero(k, precision_rounding=currency_precision) for k in res['line']]):
                continue

            # Post-processing ; creating line dictionnary, building comparison, computing total for extended, formatting
            vals = {
                'id': line.id,
                'name': line.name,
                'level': line.level,
                'columns': [{'name': l} for l in res['line']],
                'unfoldable': len(domain_ids) > 1 and line.show_domain != 'always',
                'unfolded': line.id in options.get('unfolded_lines', []) or line.show_domain == 'always',
            }
            if line.action_id:
                vals['action_id'] = line.action_id.id
            domain_ids.remove('line')
            lines = [vals]
            groupby = line.groupby or 'aml'
            if line.id in options.get('unfolded_lines', []) or line.show_domain == 'always':
                if line.groupby:
                    domain_ids = sorted(list(domain_ids), key=lambda k: line._get_gb_name(k))
                for domain_id in domain_ids:
                    name = line._get_gb_name(domain_id)
                    vals = {
                        'id': domain_id,
                        'name': name and len(name) >= 45 and name[0:40] + '...' or name,
                        'level': 1,
                        'parent_id': line.id,
                        'columns': [{'name': l} for l in res[domain_id]],
                        'caret_options': groupby == 'account_id' and 'account.account' or groupby,
                    }
                    if line.financial_report_id.name == 'Aged Receivable':
                        vals['trust'] = self.env['res.partner'].browse([domain_id]).trust
                    lines.append(vals)
                if domain_ids:
                    lines.append({
                        'id': 'total_'+str(line.id),
                        'name': _('Total') + ' ' + line.name,
                        'class': 'o_account_reports_domain_total',
                        'parent_id': line.id,
                        'columns': copy.deepcopy(lines[0]['columns']),
                    })

            for vals in lines:
                if len(comparison_table) == 2:
                    vals['columns'].append(line._build_cmp(vals['columns'][0]['name'], vals['columns'][1]['name']))
                    for i in [0, 1]:
                        vals['columns'][i] = line._format(vals['columns'][i])
                else:
                    vals['columns'] = map(line._format, vals['columns'])
                if not line.formulas:
                    vals['columns'] = [{'name': ''} for k in vals['columns']]

            if len(lines) == 1:
                new_lines = line.children_ids.get_lines(financial_report, currency_table, options, linesDicts)
                if new_lines and line.level > 0 and line.formulas:
                    divided_lines = self._divide_line(lines[0])
                    result = [divided_lines[0]] + new_lines + [divided_lines[1]]
                else:
                    result = []
                    if line.level > 0:
                        result += lines
                    result += new_lines
                    if line.level <= 0:
                        result += lines
            else:
                result = lines
            final_result_table += result

        return final_result_table


class FormulaLine(object):
    def __init__(self, obj, currency_table, financial_report, type='balance', linesDict=None):
        if linesDict is None:
            linesDict = {}
        fields = dict((fn, 0.0) for fn in ['debit', 'credit', 'balance'])
        if type == 'balance':
            fields = obj.get_balance(linesDict, currency_table, financial_report)[0]
            linesDict[obj.code] = self
        elif type in ['sum', 'sum_if_pos', 'sum_if_neg']:
            if type == 'sum_if_neg':
                obj = obj.with_context(sum_if_neg=True)
            if type == 'sum_if_pos':
                obj = obj.with_context(sum_if_pos=True)
            if obj._name == 'account.financial.html.report.line':
                fields = obj._get_sum(currency_table, financial_report)
                self.amount_residual = fields['amount_residual']
            elif obj._name == 'account.move.line':
                self.amount_residual = 0.0
                field_names = ['debit', 'credit', 'balance', 'amount_residual']
                res = obj.env['account.financial.html.report.line']._compute_line(currency_table, financial_report)
                for field in field_names:
                    fields[field] = res[field]
                self.amount_residual = fields['amount_residual']
        elif type == 'not_computed':
            for field in fields:
                fields[field] = obj.get(field, 0)
            self.amount_residual = obj.get('amount_residual', 0)
        elif type == 'null':
            self.amount_residual = 0.0
        self.balance = fields['balance']
        self.credit = fields['credit']
        self.debit = fields['debit']


class FormulaContext(dict):
    def __init__(self, reportLineObj, linesDict, currency_table, financial_report, curObj=None, only_sum=False, *data):
        self.reportLineObj = reportLineObj
        self.curObj = curObj
        self.linesDict = linesDict
        self.currency_table = currency_table
        self.only_sum = only_sum
        self.financial_report = financial_report
        return super(FormulaContext, self).__init__(data)

    def __getitem__(self, item):
        formula_items = ['sum', 'sum_if_pos', 'sum_if_neg']
        if item in set(__builtins__.keys()) - set(formula_items):
            return super(FormulaContext, self).__getitem__(item)

        if self.only_sum and item not in formula_items:
            return FormulaLine(self.curObj, self.currency_table, self.financial_report, type='null')
        if self.get(item):
            return super(FormulaContext, self).__getitem__(item)
        if self.linesDict.get(item):
            return self.linesDict[item]
        if item == 'sum':
            res = FormulaLine(self.curObj, self.currency_table, self.financial_report, type='sum')
            self['sum'] = res
            return res
        if item == 'sum_if_pos':
            res = FormulaLine(self.curObj, self.currency_table, self.financial_report, type='sum_if_pos')
            self['sum_if_pos'] = res
            return res
        if item == 'sum_if_neg':
            res = FormulaLine(self.curObj, self.currency_table, self.financial_report, type='sum_if_neg')
            self['sum_if_neg'] = res
            return res
        if item == 'NDays':
            d1 = datetime.strptime(self.curObj.env.context['date_from'], "%Y-%m-%d")
            d2 = datetime.strptime(self.curObj.env.context['date_to'], "%Y-%m-%d")
            res = (d2 - d1).days
            self['NDays'] = res
            return res
        line_id = self.reportLineObj.search([('code', '=', item)], limit=1)
        if line_id:
            strict_range = line_id.special_date_changer == 'strict_range'
            period_from = line_id._context['date_from']
            period_to = line_id._context['date_to']
            if line_id.special_date_changer == 'from_beginning':
                period_from = False
            if line_id.special_date_changer == 'to_beginning_of_period' and line_id._context.get('date_from'):
                date_tmp = datetime.strptime(line_id._context['date_from'], "%Y-%m-%d") - relativedelta(days=1)
                period_to = date_tmp.strftime('%Y-%m-%d')
                period_from = False
            res = FormulaLine(line_id.with_context(strict_range=strict_range, date_from=period_from, date_to=period_to), self.currency_table, self.financial_report, linesDict=self.linesDict)
            self.linesDict[item] = res
            return res
        return super(FormulaContext, self).__getitem__(item)


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    @api.multi
    def update_translations(self, filter_lang=None):
        """ Create missing translations after loading the one of account.financial.html.report

        Use the translations of the account.financial.html.report to translate the linked
        ir.actions.client and ir.ui.menu generated at the creation of the report
        """
        res = super(IrModuleModule, self).update_translations(filter_lang=filter_lang)

        # generated missing action translations for translated reports
        self.env.cr.execute("""
           INSERT INTO ir_translation (lang, type, name, res_id, src, value, module, state)
           SELECT l.code, 'model', 'ir.actions.client,name', a.id, t.src, t.value, t.module, t.state
             FROM account_financial_html_report r
             JOIN ir_act_client a ON (r.name = a.name)
             JOIN ir_translation t ON (t.res_id = r.id AND t.name = 'account.financial.html.report,name')
             JOIN res_lang l on  (l.code = t.lang)
            WHERE NOT EXISTS (
                  SELECT 1 FROM ir_translation tt
                  WHERE (tt.name = 'ir.actions.client,name'
                    AND tt.lang = l.code
                    AND type='model'
                    AND tt.res_id = a.id)
                  )
        """)

        # generated missing menu translations for translated reports
        self.env.cr.execute("""
           INSERT INTO ir_translation (lang, type, name, res_id, src, value, module, state)
           SELECT l.code, 'model', 'ir.ui.menu,name', m.id, t.src, t.value, t.module, t.state
             FROM account_financial_html_report r
             JOIN ir_ui_menu m ON (r.name = m.name)
             JOIN ir_translation t ON (t.res_id = r.id AND t.name = 'account.financial.html.report,name')
             JOIN res_lang l on  (l.code = t.lang)
            WHERE NOT EXISTS (
                  SELECT 1 FROM ir_translation tt
                  WHERE (tt.name = 'ir.ui.menu,name'
                    AND tt.lang = l.code
                    AND type='model'
                    AND tt.res_id = m.id)
                  )
        """)

        return res
