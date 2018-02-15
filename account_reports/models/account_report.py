# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import calendar
import copy
import json
import io
import logging
import lxml.html
import datetime

from dateutil.relativedelta import relativedelta

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter

from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, pycompat, config, date_utils
from babel.dates import get_quarter_names
from odoo.tools.misc import formatLang, format_date
from odoo.addons.web.controllers.main import clean_action
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountReportManager(models.Model):
    _name = 'account.report.manager'
    _description = 'manage summary and footnotes of reports'

    # must work with multi-company, in case of multi company, no company_id defined
    report_name = fields.Char(required=True, help='name of the model of the report')
    summary = fields.Char()
    footnotes_ids = fields.One2many('account.report.footnote', 'manager_id')
    company_id = fields.Many2one('res.company')
    financial_report_id = fields.Many2one('account.financial.html.report')

    def add_footnote(self, text, line):
        return self.env['account.report.footnote'].create({'line': line, 'text': text, 'manager_id': self.id})

class AccountReportFootnote(models.Model):
    _name = 'account.report.footnote'
    _description = 'Footnote for reports'

    text = fields.Char()
    line = fields.Char(index=True)
    manager_id = fields.Many2one('account.report.manager')

class AccountReport(models.AbstractModel):
    _name = 'account.report'

    filter_date = None
    filter_cash_basis = None
    filter_all_entries = None
    filter_comparison = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = None
    filter_hierarchy = None
    filter_partner = None

    def has_single_date_filter(self, options):
        '''Determine if we are dealing with options having a single date (options['date']['date']) or
        a date range options['date']['date_from'] -> options['date']['date_to'].

        :param options: The report options.
        :return:        True if False -> date, False otherwise (date_from -> date_to).
        '''
        return options['date'].get('date_from') is None

    def _build_options(self, previous_options=None):
        if not previous_options:
            previous_options = {}
        options = {}
        filter_list = [attr for attr in dir(self) if attr.startswith('filter_') and len(attr) > 7 and not callable(getattr(self, attr))]
        for element in filter_list:
            filter_name = element[7:]
            options[filter_name] = getattr(self, element)

        group_multi_company = self.env['ir.model.data'].xmlid_to_object('base.group_multi_company')
        if self.env.user.id in group_multi_company.users.ids:
            # We have a user with multi-company
            options['multi_company'] = [{'id': c.id, 'name': c.name, 'selected': True if c.id == self.env.user.company_id.id else False} for c in self.env.user.company_ids]
        if options.get('journals'):
            options['journals'] = self.get_journals()

        options['unfolded_lines'] = []
        # Merge old options with default from this report
        for key, value in options.items():
            if key in previous_options and value is not None and previous_options[key] is not None:
                # special case handler for date and comparison as from one report to another, they can have either a date range or single date
                if key == 'date' or key == 'comparison':
                    if key == 'comparison':
                        options[key]['number_period'] = previous_options[key]['number_period']
                    options[key]['filter'] = 'custom'
                    if previous_options[key].get('filter', 'custom') != 'custom':
                        # just copy filter and let the system compute the correct date from it
                        options[key]['filter'] = previous_options[key]['filter']
                    elif value.get('date_from') is not None and not previous_options[key].get('date_from'):
                        date = datetime.datetime.strptime(previous_options[key]['date'], DEFAULT_SERVER_DATE_FORMAT).date()
                        company_fiscalyear_dates = self.env.user.company_id.compute_fiscalyear_dates(date)
                        options[key]['date_from'] = company_fiscalyear_dates['date_from'].strftime(DEFAULT_SERVER_DATE_FORMAT)
                        options[key]['date_to'] = previous_options[key]['date']
                    elif value.get('date') is not None and not previous_options[key].get('date'):
                        options[key]['date'] = previous_options[key]['date_to']
                    else:
                        options[key] = previous_options[key]
                else:
                    options[key] = previous_options[key]
        return options

    @api.model
    def get_options(self, previous_options=None):
        # Be sure that user has group analytic if a report tries to display analytic
        if self.filter_analytic:
            self.filter_analytic_accounts = [] if self.env.user.id in self.env.ref('analytic.group_analytic_accounting').users.ids else None
            self.filter_analytic_tags = [] if self.env.user.id in self.env.ref('analytic.group_analytic_tags').users.ids else None
            #don't display the analytic filtering options if no option would be shown
            if self.filter_analytic_accounts is None and self.filter_analytic_tags is None:
                self.filter_analytic = None
        if self.filter_partner:
            self.filter_partner_ids = []
            self.filter_partner_categories = []
        return self._build_options(previous_options)

    def get_header(self, options):
        if not options.get('groups', {}).get('ids'):
            return [self.get_columns_name(options)]
        return self._get_columns_name_hierarchy(options)

    #TO BE OVERWRITTEN
    def _get_columns_name_hierarchy(self, options):
        return []

    #TO BE OVERWRITTEN
    def get_columns_name(self, options):
        return []

    #TO BE OVERWRITTEN
    def get_lines(self, options, line_id=None):
        return []

    #TO BE OVERWRITTEN
    def get_templates(self):
        return {
                'main_template': 'account_reports.main_template',
                'line_template': 'account_reports.line_template',
                'footnotes_template': 'account_reports.footnotes_template',
                'search_template': 'account_reports.search_template',
        }

    #TO BE OVERWRITTEN
    def get_report_name(self):
        return _('General Report')

    def get_report_filename(self, options):
        """The name that will be used for the file when downloading pdf,xlsx,..."""
        return self.get_report_name().lower().replace(' ', '_')

    def execute_action(self, options, params=None):
        action_id = int(params.get('actionId'))
        action = self.env['ir.actions.actions'].browse([action_id])
        action_type = action.type
        action = self.env[action.type].browse([action_id])
        action_read = action.read()[0]
        if action_type == 'ir.actions.client':
            # Check if we are opening another report and if yes, pass options and ignore_session
            if action.tag == 'account_report':
                options['unfolded_lines'] = []
                options['unfold_all'] = False
                another_report_context = safe_eval(action_read['context'])
                another_report = self.browse(another_report_context['id'])
                if not self.date_range and another_report.date_range:
                    # Don't propagate the filter if current report is date based while the targetted
                    # report is date_range based, because the semantic is not the same:
                    # 'End of Following Month' in BS != 'Last Month' in P&L (it has to go from 1st day of fiscalyear)
                    options['date'].pop('filter')
                action_read.update({'options': options, 'ignore_session': 'read'})
        if params.get('id'):
            # Add the id of the account.financial.html.report.line in the action's context
            context = action_read.get('context') and safe_eval(action_read['context']) or {}
            context.setdefault('active_id', int(params['id']))
            action_read['context'] = context
        return action_read

    @api.multi
    def open_document(self, options, params=None):
        if not params:
            params = {}
        ctx = self.env.context.copy()
        ctx.pop('id', '')
        aml_id = params.get('id')
        document = params.get('object', 'account.move')
        if aml_id:
            aml = self.env['account.move.line'].browse(aml_id)
            view_name = 'view_move_form'
            res_id = aml.move_id.id
            if document == 'account.invoice' and aml.invoice_id.id:
                res_id = aml.invoice_id.id
                if aml.invoice_id.type in ('in_refund', 'in_invoice'):
                    view_name = 'invoice_supplier_form'
                elif aml.invoice_id.type in ('out_refund', 'out_invoice'):
                    view_name = 'invoice_form'
            elif document == 'account.payment' and aml.payment_id.id:
                view_name = 'view_account_payment_form'
                res_id = aml.payment_id.id
            view_id = self.env['ir.model.data'].get_object_reference('account', view_name)[1]
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'tree',
                'view_mode': 'form',
                'views': [(view_id, 'form')],
                'res_model': document,
                'view_id': view_id,
                'res_id': res_id,
                'context': ctx,
            }

    def open_tax(self, options, params=None):
        active_id = int(str(params.get('id')).split('_')[0])
        tax = self.env['account.tax'].browse(active_id)
        domain = []
        if tax.tax_exigibility == 'on_payment':
            domain = [('tax_exigible', '=', True)]
        domain += [('date', '>=', options.get('date').get('date_from')), ('date', '<=', options.get('date').get('date_to')),
                  '|', ('tax_ids', 'in', [active_id]), ('tax_line_id', 'in', [active_id])]
        if not options.get('all_entries'):
            domain.append(('move_id.state', '=', 'posted'))
        action = self.env.ref('account.action_move_line_select_tax_audit').read()[0]
        ctx = self.env.context.copy()
        ctx.update({'active_id': active_id, 'search_default_account': 1, 'search_default_date_filter': 1,})
        action = clean_action(action)
        action['domain'] = domain
        action['context'] = ctx
        return action

    def view_too_many(self, options, params=None):
        model, active_id = params.get('actionId').split(',')
        ctx = self.env.context.copy()
        if model == 'account':
            action = self.env.ref('account.action_move_line_select').read()[0]
            ctx.update({
                'search_default_account_id': [int(active_id)],
                'active_id': int(active_id),
                })
        if model == 'partner':
            action = self.env.ref('account.action_move_line_select_by_partner').read()[0]
            ctx.update({
                'search_default_partner_id': [int(active_id)],
                'active_id': int(active_id),
                })
        action = clean_action(action)
        action['context'] = ctx
        return action

    @api.multi
    def open_general_ledger(self, options, params=None):
        if not params:
            params = {}
        ctx = self.env.context.copy()
        ctx.pop('id', '')
        action = self.env.ref('account_reports.action_account_report_general_ledger').read()[0]
        options['unfolded_lines'] = ['account_%s' % (params.get('id', ''),)]
        options['unfold_all'] = False
        ctx.update({'model': 'account.general.ledger'})
        action.update({'options': options, 'context': ctx, 'ignore_session': 'read'})
        return action

    def open_journal_items(self, options, params):
        action = self.env.ref('account.action_move_line_select').read()[0]
        action = clean_action(action)
        ctx = self.env.context.copy()

        if params and 'id' in params:
            active_id = params['id']
            ctx.update({
                    'search_default_account_id': [active_id],
            })
            action['context'] = ctx
        return action

    def reverse(self, values):
        """Utility method used to reverse a list, this method is used during template generation in order to reverse periods for example"""
        if type(values) != list:
            return values
        else:
            inv_values = copy.deepcopy(values)
            inv_values.reverse()
        return inv_values

    def set_context(self, options):
        """This method will set information inside the context based on the options dict as some options need to be in context for the query_get method defined in account_move_line"""
        ctx = self.env.context.copy()
        if options.get('cash_basis'):
            ctx['cash_basis'] = True
        if options.get('date') and options['date'].get('date_from'):
            ctx['date_from'] = options['date']['date_from']
        if options.get('date'):
            ctx['date_to'] = options['date'].get('date_to') or options['date'].get('date')
        if options.get('all_entries') is not None:
            ctx['state'] = options.get('all_entries') and 'all' or 'posted'
        if options.get('journals'):
            ctx['journal_ids'] = [j.get('id') for j in options.get('journals') if j.get('selected')]
        company_ids = []
        if options.get('multi_company'):
            company_ids = [c.get('id') for c in options['multi_company'] if c.get('selected')]
            company_ids = company_ids if len(company_ids) > 0 else [c.get('id') for c in options['multi_company']]
        ctx['company_ids'] = len(company_ids) > 0 and company_ids or [self.env.user.company_id.id]
        if options.get('analytic_accounts'):
            ctx['analytic_account_ids'] = self.env['account.analytic.account'].browse([int(acc) for acc in options['analytic_accounts']])
        if options.get('analytic_tags'):
            ctx['analytic_tag_ids'] = self.env['account.analytic.tag'].browse([int(t) for t in options['analytic_tags']])
        if options.get('partner_ids'):
            ctx['partner_ids'] = self.env['res.partner'].browse([int(partner) for partner in options['partner_ids']])
        if options.get('partner_categories'):
            ctx['partner_categories'] = self.env['res.partner.category'].browse([int(category) for category in options['partner_categories']])
        return ctx

    @api.multi
    def get_report_informations(self, options):
        '''
        return a dictionary of informations that will be needed by the js widget, manager_id, footnotes, html of report and searchview, ...
        '''
        options = self.get_options(options)
        # apply date and date_comparison filter
        self.apply_date_filter(options)

        searchview_dict = {'options': options, 'context': self.env.context}
        # Check if report needs analytic
        if options.get('analytic_accounts') is not None:
            searchview_dict['analytic_accounts'] = self.env.user.id in self.env.ref('analytic.group_analytic_accounting').users.ids and [(t.id, t.name) for t in self.env['account.analytic.account'].search([])] or False
            options['selected_analytic_account_names'] = [self.env['account.analytic.account'].browse(int(account)).name for account in options['analytic_accounts']]
        if options.get('analytic_tags') is not None:
            searchview_dict['analytic_tags'] = self.env.user.id in self.env.ref('analytic.group_analytic_tags').users.ids and [(t.id, t.name) for t in self.env['account.analytic.tag'].search([])] or False
            options['selected_analytic_tag_names'] = [self.env['account.analytic.tag'].browse(int(tag)).name for tag in options['analytic_tags']]
        if options.get('partner'):
            searchview_dict['res_partners'] = [(partner.id, partner.name) for partner in self.env['res.partner'].search([])] or False
            searchview_dict['res_partner_categories'] = [(category.id, category.name) for category in self.env['res.partner.category'].search([])] or False
            options['selected_partner_ids'] = [self.env['res.partner'].browse(int(partner)).name for partner in options['partner_ids']]
            options['selected_partner_categories'] = [self.env['res.partner.category'].browse(int(category)).name for category in options['partner_categories']]

        report_manager = self.get_report_manager(options)
        info = {'options': options,
                'context': self.env.context,
                'report_manager_id': report_manager.id,
                'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
                'buttons': self.get_reports_buttons(),
                'main_html': self.get_html(options),
                'searchview_html': self.env['ir.ui.view'].render_template(self.get_templates().get('search_template', 'account_report.search_template'), values=searchview_dict),
                }
        return info

    def create_hierarchy(self, lines):
        """This method is called when the option 'hiearchy' is enabled on a report.
        It receives the lines (as computed by get_lines()) in argument, and will add
        a hiearchy in those lines by using the account.group of accounts. If not set,
        it will fallback on creating a hierarchy based on the account's code first 3
        digits.
        """
        AccountAccount = self.env['account.account']
        hierarchy_list = {}
        current_position = 0

        for line in lines:
            columns = line.get('columns', [{}])
            is_grouped_by_account = line.get('caret_options') == 'account.account'
            account_id = AccountAccount.browse(line.get('id')) if is_grouped_by_account else AccountAccount
            group_id = account_id.group_id
            if group_id:
                group_prefix = group_id.code_prefix
                group_name = group_id.name
                group_key = group_id
            else:
                group_name = ''
                group_prefix = account_id.code and account_id.code[0:3] or False
                group_key = group_prefix

            current_group_level = is_grouped_by_account and 4 or line.get('level', 4)
            while group_key:
                #create hierarchy leaves if needed
                if group_key not in hierarchy_list:
                    current_group_level -= 1
                    hierarchy_list[group_key] = {
                        'position': (current_position, current_group_level),  # will be used to insert at the good place
                        'values': {
                            'id': 'hierarchy_%s_%s' % (current_position, current_group_level),
                            'name': '%s %s' % (group_prefix, group_name) if group_prefix else group_name,
                            'unfoldable': False,
                            'unfolded': True,
                            'parent_id': line.get('parent_id'),  # to make these fold when the original parent gets folded
                            'level': current_group_level,
                            'columns': [0 for l in range(len(columns))],
                        }
                    }

                #sum line values in hierarchy leaves
                hierarchy_list[group_key]['values']['columns'] = [sum(x) for x in pycompat.izip(hierarchy_list[group_key]['values']['columns'], [c.get('no_format_name', 0) for c in columns])]

                #loop on
                if account_id.group_id:
                    group_key = group_key.parent_id
                    group_prefix = group_key.code_prefix
                    group_name = group_key.name
                else:
                    group_prefix = group_prefix[:-1]
                    group_name = ''
                    group_key = group_prefix

            #count the number of lines passed
            current_position += 1

        #build the final list that will be return
        already_inserted = 0
        for key in sorted(hierarchy_list, key=lambda x:hierarchy_list[x]['position']):
            value = hierarchy_list[key]
            value['values']['columns'] = [{'name': self.format_value(v)} for v in value['values']['columns']]
            lines.insert(value['position'][0] + already_inserted, value['values'])
            already_inserted += 1
        return lines

    @api.multi
    def get_html(self, options, line_id=None, additional_context=None):
        '''
        return the html value of report, or html value of unfolded line
        * if line_id is set, the template used will be the line_template
        otherwise it uses the main_template. Reason is for efficiency, when unfolding a line in the report
        we don't want to reload all lines, just get the one we unfolded.
        '''
        templates = self.get_templates()
        report_manager = self.get_report_manager(options)
        report = {'name': self.get_report_name(),
                'summary': report_manager.summary,
                'company_name': self.env.user.company_id.name,}
        lines = self.with_context(self.set_context(options)).get_lines(options, line_id=line_id)

        if options.get('hierarchy'):
            lines = self.create_hierarchy(lines)

        footnotes_to_render = []
        if self.env.context.get('print_mode', False):
            # we are in print mode, so compute footnote number and include them in lines values, otherwise, let the js compute the number correctly as
            # we don't know all the visible lines.
            footnotes = dict([(str(f.line), f) for f in report_manager.footnotes_ids])
            number = 0
            for line in lines:
                f = footnotes.get(str(line.get('id')))
                if f:
                    number += 1
                    line['footnote'] = str(number)
                    footnotes_to_render.append({'id': f.id, 'number': number, 'text': f.text})

        rcontext = {'report': report,
                    'lines': {'columns_header': self.get_header(options), 'lines': lines},
                    'options': options,
                    'context': self.env.context,
                    'model': self,
                }
        if additional_context and type(additional_context) == dict:
            rcontext.update(additional_context)
        render_template = templates.get('main_template', 'account_reports.main_template')
        if line_id is not None:
            render_template = templates.get('line_template', 'account_reports.line_template')
        html = self.env['ir.ui.view'].render_template(
            render_template,
            values=dict(rcontext),
        )
        if self.env.context.get('print_mode', False):
            for k,v in self.replace_class().items():
                html = html.replace(k, v)
            # append footnote as well
            html = html.replace(b'<div class="js_account_report_footnotes"></div>', self.get_html_footnotes(footnotes_to_render))
        return html

    @api.multi
    def get_html_footnotes(self, footnotes):
        template = self.get_templates().get('footnotes_template', 'account_reports.footnotes_template')
        rcontext = {'footnotes': footnotes, 'context': self.env.context}
        html = self.env['ir.ui.view'].render_template(template, values=dict(rcontext))
        return html

    def get_reports_buttons(self):
        return [{'name': _('Print Preview'), 'action': 'print_pdf'}, {'name': _('Export (XLSX)'), 'action': 'print_xlsx'}]

    def get_report_manager(self, options):
        domain = [('report_name', '=', self._name)]
        domain = (domain + [('financial_report_id', '=', self.id)]) if 'id' in dir(self) else domain
        selected_companies = []
        if options.get('multi_company'):
            selected_companies = [c['id'] for c in options['multi_company'] if c.get('selected')]
        if len(selected_companies) == 1:
            domain += [('company_id', '=', selected_companies[0])]
        existing_manager = self.env['account.report.manager'].search(domain, limit=1)
        if not existing_manager:
            existing_manager = self.env['account.report.manager'].create({'report_name': self._name, 'company_id': selected_companies and selected_companies[0] or False, 'financial_report_id': self.id if 'id' in dir(self) else False})
        return existing_manager

    def _get_filter_journals(self):
        return self.env['account.journal'].search([('company_id', 'in', self.env.user.company_ids.ids or [self.env.user.company_id.id])], order="company_id, name")

    def get_journals(self):
        journals_read = self._get_filter_journals()
        journals = []
        previous_company = False
        for c in journals_read:
            if c.company_id != previous_company:
                journals.append({'id': 'divider', 'name': c.company_id.name})
                previous_company = c.company_id
            journals.append({'id': c.id, 'name': c.name, 'code': c.code, 'type': c.type, 'selected': False})
        return journals

    def _get_dates_period(self, options, date_from, date_to, period_type=None):
        '''Compute some information about the period:
        * The name to display on the report.
        * The period type (e.g. quarter) if not specified explicitly.

        :param options:     The report options.
        :param date_from:   The starting date of the period.
        :param date_to:     The ending date of the period.
        :param period_type: The type of the interval date_from -> date_to.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        def match(dt_from, dt_to):
            if self.has_single_date_filter(options):
                return (date_to or date_from) == dt_to
            else:
                return (dt_from, dt_to) == (date_from, date_to)

        string = None
        # If no date_from or not date_to, we are unable to determine a period
        if not period_type:
            date = date_to or date_from
            company_fiscalyear_dates = self.env.user.company_id.compute_fiscalyear_dates(date)
            if match(company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to']):
                period_type = 'fiscalyear'
                if company_fiscalyear_dates.get('record'):
                    string = company_fiscalyear_dates['record'].name
            elif match(*date_utils.get_month(date)):
                period_type = 'month'
            elif match(*date_utils.get_quarter(date)):
                period_type = 'quarter'
            elif match(*date_utils.get_fiscal_year(date)):
                period_type = 'year'
            else:
                period_type = 'custom'

        if not string:
            fy_day = self.env.user.company_id.fiscalyear_last_day
            fy_month = self.env.user.company_id.fiscalyear_last_month
            if self.has_single_date_filter(options):
                string = _('As of %s') % (format_date(self.env, date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)))
            elif period_type == 'year' or (period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to)):
                string = date_to.strftime('%Y')
            elif period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to, day=fy_day, month=fy_month):
                string = '%s - %s' % (date_to.year - 1, date_to.year)
            elif period_type == 'month':
                string = format_date(self.env, date_to.strftime(DEFAULT_SERVER_DATE_FORMAT), date_format='MMM YYYY')
            elif period_type == 'quarter':
                quarter_names = get_quarter_names('abbreviated', locale=self.env.context.get('lang') or 'en_US')
                string = u'%s\N{NO-BREAK SPACE}%s' % (quarter_names[date_utils.get_quarter_number(date_to)], date_to.year)
            else:
                dt_from_str = format_date(self.env, date_from.strftime(DEFAULT_SERVER_DATE_FORMAT))
                dt_to_str = format_date(self.env, date_to.strftime(DEFAULT_SERVER_DATE_FORMAT))
                string = _('From %s \n to  %s') % (dt_from_str, dt_to_str)

        return {
            'string': string,
            'period_type': period_type,
            'date_from': date_from,
            'date_to': date_to,
        }

    def _get_dates_previous_period(self, options, period_vals):
        '''Shift the period to the previous one.

        :param options:     The report options.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        date_from = period_vals['date_from']
        date_to = period_vals['date_to']

        if not date_from or not date_to:
            date = (date_from or date_to).replace(day=1) - datetime.timedelta(days=1)
            # Propagate the period_type to avoid bad behavior.
            # E.g. custom single date 2018-01-30 with previous period will produce 2017-12-31 that
            # must not be interpreted as a fiscal year.
            return self._get_dates_period(options, None, date, period_type=period_type)

        date_to = date_from - datetime.timedelta(days=1)
        if period_type == 'fiscalyear':
            # Don't pass the period_type to _get_dates_period to be able to retrieve the account.fiscal.year record if
            # necessary.
            company_fiscalyear_dates = self.env.user.company_id.compute_fiscalyear_dates(date_to)
            return self._get_dates_period(options, company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to'])
        if period_type == 'month':
            return self._get_dates_period(options, *date_utils.get_month(date_to), period_type='month')
        if period_type == 'quarter':
            return self._get_dates_period(options, *date_utils.get_quarter(date_to), period_type='quarter')
        if period_type == 'year':
            return self._get_dates_period(options, *date_utils.get_fiscal_year(date_to), period_type='year')
        date_from = date_to - datetime.timedelta(days=(date_to - date_from).days)
        return self._get_dates_period(options, date_from, date_to)

    def _get_dates_previous_year(self, options, period_vals):
        '''Shift the period to the previous year.

        :param options:     The report options.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        date_from = period_vals['date_from']
        date_to = period_vals['date_to']

        # Note: Use relativedelta to avoid moving from 2016-02-29 -> 2015-02-29 and then, have a day out of range.
        if not date_from or not date_to:
            date_to = date_from or date_to
            date_from = None

        date_to = date_to - relativedelta(years=1)
        # Take care about the 29th february.
        # Moving from 2017-02-28 -> 2016-02-28 is wrong! It must be 2016-02-29.
        if period_type == 'month':
            date_from, date_to = date_utils.get_month(date_to)
        elif date_from:
            date_from = date_from - relativedelta(years=1)
        return self._get_dates_period(options, date_from, date_to, period_type=period_type)

    def format_value(self, value, currency=False):
        if self.env.context.get('no_format'):
            return value
        currency_id = currency or self.env.user.company_id.currency_id
        if currency_id.is_zero(value):
            # don't print -0.0 in reports
            value = abs(value)
        res = formatLang(self.env, value, currency_obj=currency_id)
        return res

    def _format_aml_name(self, aml):
        name = '-'.join(
            (aml.move_id.name not in ['', '/'] and [aml.move_id.name] or []) +
            (aml.ref not in ['', '/', False] and [aml.ref] or []) +
            ([aml.name] if aml.name and aml.name not in ['', '/'] else [])
        )
        if len(name) > 35 and not self.env.context.get('no_format'):
            name = name[:32] + "..."
        return name

    def format_date(self, options, dt_filter='date'):
        # previously get_full_date_names
        if self.has_single_date_filter(options):
            dt_from = None
            dt_to = datetime.datetime.strptime(options[dt_filter]['date'], DEFAULT_SERVER_DATE_FORMAT).date()
        else:
            dt_from = datetime.datetime.strptime(options[dt_filter]['date_from'], DEFAULT_SERVER_DATE_FORMAT).date()
            dt_to = datetime.datetime.strptime(options[dt_filter]['date_to'], DEFAULT_SERVER_DATE_FORMAT).date()

        return self._get_dates_period(options, dt_from, dt_to)['string']

    def apply_date_filter(self, options):
        def create_vals(period_vals):
            vals = {'string': period_vals['string']}
            if self.has_single_date_filter(options):
                vals['date'] = (period_vals['date_to'] or period_vals['date_from']).strftime(DEFAULT_SERVER_DATE_FORMAT)
            else:
                vals['date_from'] = period_vals['date_from'].strftime(DEFAULT_SERVER_DATE_FORMAT)
                vals['date_to'] = period_vals['date_to'].strftime(DEFAULT_SERVER_DATE_FORMAT)
            return vals

        # ===== Date Filter =====
        if not options.get('date') or not options['date'].get('filter'):
            return
        options_filter = options['date']['filter']

        date_from = None
        date_to = datetime.date.today()
        if options_filter == 'custom':
            if self.has_single_date_filter(options):
                date_from = None
                date_to = datetime.datetime.strptime(options['date']['date'], DEFAULT_SERVER_DATE_FORMAT).date()
            else:
                date_from = datetime.datetime.strptime(options['date']['date_from'], DEFAULT_SERVER_DATE_FORMAT).date()
                date_to = datetime.datetime.strptime(options['date']['date_to'], DEFAULT_SERVER_DATE_FORMAT).date()
        elif 'today' in options_filter:
            if not self.has_single_date_filter(options):
                date_from = self.env.user.company_id.compute_fiscalyear_dates(date_to)['date_from']
        elif 'month' in options_filter:
            date_from, date_to = date_utils.get_month(date_to)
        elif 'quarter' in options_filter:
            date_from, date_to = date_utils.get_quarter(date_to)
        elif 'year' in options_filter:
            company_fiscalyear_dates = self.env.user.company_id.compute_fiscalyear_dates(date_to)
            date_from = company_fiscalyear_dates['date_from']
            date_to = company_fiscalyear_dates['date_to']
        else:
            raise UserError('Programmation Error: Unrecognized parameter %s in date filter!' % str(options_filter))

        period_vals = self._get_dates_period(options, date_from, date_to)
        if 'last' in options_filter:
            period_vals = self._get_dates_previous_period(options, period_vals)

        options['date'].update(create_vals(period_vals))

        # ===== Comparison Filter =====
        if not options.get('comparison') or not options['comparison'].get('filter'):
            return
        cmp_filter = options['comparison']['filter']

        if cmp_filter == 'no_comparison':
            options['comparison']['string'] = _('No comparison')
            options['comparison']['periods'] = []
            if self.has_single_date_filter(options):
                options['comparison']['date'] = ""
            else:
                options['comparison']['date_from'] = ""
                options['comparison']['date_to'] = ""
            return

        if cmp_filter == 'custom':
            if self.has_single_date_filter(options):
                date_from = None
                date_to = datetime.datetime.strptime(options['comparison']['date'], DEFAULT_SERVER_DATE_FORMAT).date()
            else:
                date_from = datetime.datetime.strptime(options['comparison']['date_from'], DEFAULT_SERVER_DATE_FORMAT).date()
                date_to = datetime.datetime.strptime(options['comparison']['date_to'], DEFAULT_SERVER_DATE_FORMAT).date()
            vals = create_vals(self._get_dates_period(options, date_from, date_to))
            options['comparison']['periods'] = [vals]
            return

        periods = []
        number_period = options['comparison'].get('number_period', 1) or 0
        for index in range(0, number_period):
            if cmp_filter == 'previous_period':
                period_vals = self._get_dates_previous_period(options, period_vals)
            else:
                period_vals = self._get_dates_previous_year(options, period_vals)
            periods.append(create_vals(period_vals))

        if len(periods) > 0:
            options['comparison'].update(periods[0])
        options['comparison']['periods'] = periods

    def print_pdf(self, options):
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'pdf',
                         'financial_id': self.env.context.get('id'),
                         }
                }

    def replace_class(self):
        """When printing pdf, we sometime want to remove/add/replace class for the report to look a bit different on paper
        this method is used for this, it will replace occurence of value key by the dict value in the generated pdf
        """
        return {b'o_account_reports_no_print': b'', b'table-responsive': b'', b'<a': b'<span', b'</a>': b'</span>'}

    def get_pdf(self, options, minimal_layout=True):
        # As the assets are generated during the same transaction as the rendering of the
        # templates calling them, there is a scenario where the assets are unreachable: when
        # you make a request to read the assets while the transaction creating them is not done.
        # Indeed, when you make an asset request, the controller has to read the `ir.attachment`
        # table.
        # This scenario happens when you want to print a PDF report for the first time, as the
        # assets are not in cache and must be generated. To workaround this issue, we manually
        # commit the writes in the `ir.attachment` table. It is done thanks to a key in the context.
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.user.company_id,
        }

        body = self.env['ir.ui.view'].render_template(
            "account_reports.print_template",
            values=dict(rcontext),
        )
        body_html = self.with_context(print_mode=True).get_html(options)

        body = body.replace(b'<body class="o_account_reports_body_print">', b'<body class="o_account_reports_body_print">' + body_html)
        if minimal_layout:
            header = ''
            footer = self.env['ir.actions.report'].render_template("web.internal_layout", values=rcontext)
            spec_paperformat_args = {'data-report-margin-top': 10, 'data-report-header-spacing': 10}
            footer = self.env['ir.actions.report'].render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=footer))
        else:
            rcontext.update({
                    'css': '',
                    'o': self.env.user,
                    'res_company': self.env.user.company_id,
                })
            header = self.env['ir.actions.report'].render_template("web.external_layout", values=rcontext)
            header = header.decode('utf-8') # Ensure that headers and footer are correctly encoded
            spec_paperformat_args = {}
            # parse header as new header contains header, body and footer
            try:
                root = lxml.html.fromstring(header)
                match_klass = "//div[contains(concat(' ', normalize-space(@class), ' '), ' {} ')]"

                for node in root.xpath(match_klass.format('header')):
                    headers = lxml.html.tostring(node)
                    headers = self.env['ir.actions.report'].render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=headers))

                for node in root.xpath(match_klass.format('footer')):
                    footer = lxml.html.tostring(node)
                    footer = self.env['ir.actions.report'].render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=footer))

            except lxml.etree.XMLSyntaxError:
                headers = header
                footer = ''
            header = headers

        landscape = False
        if len(self.with_context(print_mode=True).get_header(options)[-1]) > 5:
            landscape = True

        return self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            header=header, footer=footer,
            landscape=landscape,
            specific_paperformat_args=spec_paperformat_args
        )

    def print_xlsx(self, options):
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'xlsx',
                         'financial_id': self.env.context.get('id'),
                         }
                }

    def _get_super_columns(self, options):
        """
        Essentially used when getting the xlsx of a report
        Some reports may need super title cells on top of regular
        columns title, This methods retrieve the formers.
        e.g. in Trial Balance, you can compare periods (super cells)
            and each have debit/credit columns


        @params {dict} options: options for computing the report
        @return {dict}:
            {list(dict)} columns: the dict of the super columns of the xlsx report,
                the columns' string is contained into the 'string' key
            {int} merge: optional parameter. Indicates to xlsxwriter
                that it should put the contents of each column into the resulting
                cell of the merge of this [merge] number of cells
                -- only merging on one line is supported
            {int} x_offset: tells xlsxwriter it should start writing the columns from
                [x_offset] cells on the left
        """
        return {}

    def get_xlsx(self, options, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(self.get_report_name()[:31])

        def_style = workbook.add_format({'font_name': 'Arial'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        super_col_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'align': 'center'})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_0_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_0_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2})
        level_1_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2})
        level_1_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2})
        level_2_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'left': 2})
        level_2_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'right': 2})
        level_3_style = def_style
        level_3_style_left = workbook.add_format({'font_name': 'Arial', 'left': 2})
        level_3_style_right = workbook.add_format({'font_name': 'Arial', 'right': 2})
        domain_style = workbook.add_format({'font_name': 'Arial', 'italic': True})
        domain_style_left = workbook.add_format({'font_name': 'Arial', 'italic': True, 'left': 2})
        domain_style_right = workbook.add_format({'font_name': 'Arial', 'italic': True, 'right': 2})
        upper_line_style = workbook.add_format({'font_name': 'Arial', 'top': 2})

        sheet.set_column(0, 0, 15) #  Set the first column width to 15

        super_columns = self._get_super_columns(options)
        y_offset = bool(super_columns.get('columns')) and 1 or 0

        sheet.write(y_offset, 0, '', title_style)

        # Todo in master: Try to put this logic elsewhere
        x = super_columns.get('x_offset', 0)
        for super_col in super_columns.get('columns', []):
            cell_content = super_col.get('string', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
            x_merge = super_columns.get('merge')
            if x_merge and x_merge > 1:
                sheet.merge_range(0, x, 0, x + (x_merge - 1), cell_content, super_col_style)
                x += x_merge
            else:
                sheet.write(0, x, cell_content, super_col_style)
                x += 1

        for row in self.get_header(options):
            x = 0
            for column in row:
                colspan = column.get('colspan', 1)
                header_label = column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
                if colspan == 1:
                    sheet.write(y_offset, x, header_label, title_style)
                else:
                    sheet.merge_range(y_offset, x, y_offset, x + colspan - 1, header_label, title_style)
                x += colspan
            y_offset += 1
        ctx = self.set_context(options)
        ctx.update({'no_format':True, 'print_mode':True})
        lines = self.with_context(ctx).get_lines(options)

        if options.get('hierarchy'):
            lines = self.create_hierarchy(lines)

        if lines:
            max_width = max([len(l['columns']) for l in lines])

        for y in range(0, len(lines)):
            if lines[y].get('level') == 0:
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_0_style_left
                style_right = level_0_style_right
                style = level_0_style
            elif lines[y].get('level') == 1:
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_1_style_left
                style_right = level_1_style_right
                style = level_1_style
            elif lines[y].get('level') == 2:
                style_left = level_2_style_left
                style_right = level_2_style_right
                style = level_2_style
            elif lines[y].get('level') == 3:
                style_left = level_3_style_left
                style_right = level_3_style_right
                style = level_3_style
            # elif lines[y].get('type') != 'line':
            #     style_left = domain_style_left
            #     style_right = domain_style_right
            #     style = domain_style
            else:
                style = def_style
                style_left = def_style
                style_right = def_style
            sheet.write(y + y_offset, 0, lines[y]['name'], style_left)
            for x in range(1, max_width - len(lines[y]['columns']) + 1):
                sheet.write(y + y_offset, x, None, style)
            for x in range(1, len(lines[y]['columns']) + 1):
                # if isinstance(lines[y]['columns'][x - 1], tuple):
                    # lines[y]['columns'][x - 1] = lines[y]['columns'][x - 1][0]
                if x < len(lines[y]['columns']):
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, lines[y]['columns'][x - 1].get('name', ''), style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, lines[y]['columns'][x - 1].get('name', ''), style_right)
            if 'total' in lines[y].get('class', '') or lines[y].get('level') == 0:
                for x in range(len(lines[0]['columns']) + 1):
                    sheet.write(y + 1 + y_offset, x, None, upper_line_style)
                y_offset += 1
        if lines:
            for x in range(max_width + 1):
                sheet.write(len(lines) + y_offset, x, None, upper_line_style)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def print_xml(self, options):
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'xml',
                         'financial_id': self.env.context.get('id'),
                         }
                }

    def get_xml(self, options):
        return False

    def print_txt(self, options):
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'txt',
                         'financial_id': self.env.context.get('id'),
                         }
                }

    def get_txt(self, options):
        return False
