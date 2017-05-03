# -*- coding: utf-8 -*-

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.addons.web_grid.models import END_OF, STEP_BY, START_OF
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import float_round


class AnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    name = fields.Char(required=False)
    # reset amount on copy
    amount = fields.Monetary(copy=False)
    validated = fields.Boolean("Validated line", compute='_compute_timesheet_validated', store=True, compute_sudo=True)
    is_timesheet = fields.Boolean(
        string="Timesheet Line",
        compute='_compute_is_timesheet', search='_search_is_timesheet',
        help="Set if this analytic line represents a line of timesheet.")
    task_id = fields.Many2one(group_expand='_read_group_task_ids')

    @api.depends('date', 'employee_id.timesheet_validated')
    def _compute_timesheet_validated(self):
        for line in self:
            # get most recent validation date on any of the line user's employees
            validated_to = line.employee_id.timesheet_validated

            if validated_to:
                line.validated = line.date <= validated_to
            else:
                line.validated = False

    @api.multi
    @api.depends('project_id')
    def _compute_is_timesheet(self):
        for line in self:
            line.is_timesheet = bool(line.project_id)

    def _search_is_timesheet(self, operator, value):
        if (operator, value) in [('=', True), ('!=', False)]:
            return [('project_id', '!=', False)]
        return [('project_id', '=', False)]

    @api.model
    def _read_group_task_ids(self, tasks, domain, order):
        """ Display tasks with timesheet for the last grid period (defined from context) """
        if self.env.context.get('grid_anchor'):
            anchor = fields.Date.from_string(self.env.context['grid_anchor'])
        else:
            anchor = date.today() + relativedelta(weeks=-1, days=1, weekday=0)
        span = self.env.context.get('grid_range', {'span': 'week'})['span']
        date_ago = fields.Date.to_string(anchor - STEP_BY[span] + START_OF[span])

        tasks |= self.env['account.analytic.line'].search([
            ('user_id', '=', self.env.user.id),
            ('date', '>=', date_ago)
        ]).mapped('task_id')
        return tasks

    @api.multi
    def action_validate_timesheet(self):
        if self.env.context.get('grid_anchor'):
            anchor = fields.Date.from_string(self.env.context['grid_anchor'])
        else:
            anchor = date.today() + relativedelta(weeks=-1, days=1, weekday=0)
        span = self.env.context.get('grid_range', {'span': 'week'})['span']
        validate_to = fields.Date.to_string(anchor + END_OF[span])

        if not self:
            raise UserError(_("There aren't any timesheet to validate"))

        employees = self.mapped('employee_id')
        validable_employees = employees.filtered(lambda e: not e.timesheet_validated or e.timesheet_validated < validate_to)
        if not validable_employees:
            raise UserError(_('All selected timesheets are already validated'))

        validation = self.env['timesheet.validation'].create({
            'validation_date': validate_to,
            'validation_line_ids': [
                (0, 0, {'employee_id': employee.id}) for employee in validable_employees
            ]
        })

        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_model': 'timesheet.validation',
            'res_id': validation.id,
            'views': [(False, 'form')],
        }

    @api.multi
    def adjust_grid(self, row_domain, column_field, column_value, cell_field, change):
        if column_field != 'date' or cell_field != 'unit_amount':
            raise ValueError(
                "{} can only adjust unit_amount (got {}) by date (got {})".format(
                    self._name,
                    cell_field,
                    column_field,
                ))

        additionnal_domain = self._get_adjust_grid_domain(column_value)
        domain = expression.AND([row_domain, additionnal_domain])
        line = self.search(domain, limit=1, order="create_date DESC")

        if line:  # update existing line
            line.write({
                cell_field: line[cell_field] + change
            })
        else:  # create new one
            day = column_value.split('/')[0]
            self.search(row_domain, limit=1).copy({
                'name': False,
                column_field: day,
                cell_field: change
            })
        return False

    def _get_adjust_grid_domain(self, column_value):
        # span is always daily and value is an iso range
        day = column_value.split('/')[0]
        return [('name', '=', False), ('date', '=', day)]

    @api.model
    def _cron_email_get_period(self, cron_xmlid):
        """ calculate the cron period """
        cron = self.env.ref(cron_xmlid)
        date_stop = fields.Date.today()
        if cron.interval_type == 'months':
            date_start = date.today() + relativedelta(day=1, days=-1)
        else:
            date_start = date.today() - timedelta(days=datetime.now().weekday()+1)
        date_start = fields.Date.to_string(date_start)
        return date_start, date_stop

    @api.model
    def _cron_email_reminder_user(self):
        """ Send an email reminder to the user having at least one timesheet since the last 3 month. From those ones, we exclude
            ones having complete their timesheet (meaning timesheeted the same hours amount than their working calendar).
        """
        # get the employee that have at least a timesheet for the last 3 months
        users = self.search([
            ('date', '>=', fields.Date.to_string(date.today() - relativedelta(months=3))),
            ('date', '<=', fields.Date.today()),
        ]).mapped('user_id')

        # calculate the cron period
        date_start, date_stop = self._cron_email_get_period('timesheet_grid.timesheet_reminder_user')

        # get the related employees timesheet status for the cron period
        employees = self.env['hr.employee'].search([('user_id', 'in', users.ids)])
        work_hours_struct = employees.get_timesheet_and_working_hours(date_start, date_stop)

        for employee in employees:
            if employee.user_id and work_hours_struct[employee.id]['timesheet_hours'] < work_hours_struct[employee.id]['working_hours']:
                self._cron_send_email_reminder(
                    employee,
                    'timesheet_grid.mail_template_timesheet_reminder_user',
                    'hr_timesheet.act_hr_timesheet_line',
                    additionnal_values=work_hours_struct[employee.id],
                )

    @api.model
    def _cron_email_reminder_manager(self):
        """ Send a email reminder to all users having the group 'timesheet manager'. """
        date_start, date_stop = self._cron_email_get_period('timesheet_grid.timesheet_reminder_manager')
        values = {
            'date_start': date_start,
            'date_stop': date_stop,
        }
        users = self.env['res.users'].search([('groups_id', 'in', [self.env.ref('hr_timesheet.group_timesheet_manager').id])])
        self._cron_send_email_reminder(
            self.env['hr.employee'].search([('user_id', 'in', users.ids)]),
            'timesheet_grid.mail_template_timesheet_reminder_manager',
            'timesheet_grid.action_timesheet_previous_week',
            additionnal_values=values)

    @api.model
    def _cron_send_email_reminder(self, employees, template_xmlid, action_xmlid, additionnal_values=None):
        """ Send the email reminder to specified users
            :param user_ids : list of user identifier to send the reminder
            :param template_xmlid : xml id of the reminder mail template
        """
        action_url = '%s/web#menu_id=%s&action=%s' % (
            self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
            self.env.ref('hr_timesheet.timesheet_menu_root').id,
            self.env.ref(action_xmlid).id,
        )

        # send mail template to users having email address
        template = self.env.ref(template_xmlid)
        template_ctx = {'action_url': action_url}
        if additionnal_values:
            template_ctx.update(additionnal_values)

        for employee in employees.filtered('user_id'):
            template.with_context(lang=employee.user_id.lang, **template_ctx).send_mail(employee.id)


class Employee(models.Model):
    _inherit = 'hr.employee'

    timesheet_validated = fields.Date(
        "Timesheets Validation Date",
        help="Date until which the employee's timesheets have been validated")
    timesheet_manager_id = fields.Many2one(
        'res.users', string='Timesheet Responsible',
        domain=lambda self: [('groups_id', 'in', self.env.ref('hr_timesheet.group_timesheet_manager').id)],
        help="User responsible of timesheet validation. Should be Timesheet Manager.")

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        if self.parent_id:
            self.timesheet_manager_id = self.parent_id.user_id

    @api.multi
    def get_timesheet_and_working_hours(self, date_start, date_stop):
        """ Get the difference between the supposed working hour (based on resource calendar) and
            the timesheeted hours, for the given period `date_start` - `date_stop`.
            :param date_start : start date of the period to check (string)
            :param date_stop : end date of the period to check (string)
            :returns dict : a dict mapping the employee_id with his timesheeted and working hours for the
                given period.
        """
        employees = self.filtered(lambda emp: emp.resource_calendar_id)

        result = dict.fromkeys(self.ids, dict(timesheet_hours=0.0, working_hours=0.0, date_start=date_start, date_stop=date_stop))

        # find timesheeted hours of employees with working hours
        self.env.cr.execute("""
            SELECT A.employee_id as employee_id, sum(A.unit_amount) as amount_sum
            FROM account_analytic_line A
            WHERE A.employee_id IN %s AND date >= %s AND date <= %s
            GROUP BY A.employee_id
        """, (tuple(employees.ids), date_start, date_stop))
        for data_row in self.env.cr.dictfetchall():
            result[data_row['employee_id']]['timesheet_hours'] = float_round(data_row['amount_sum'], 2)

        # find working hours for the given period of employees with working calendar
        for employee in employees:
            working_hours = employee.resource_calendar_id.get_work_hours_count(
                fields.Datetime.from_string(date_start),
                fields.Datetime.from_string(date_stop),
                compute_leaves=False, resource_id=employee.resource_id.id
            )
            result[employee.id]['working_hours'] = float_round(working_hours, 2)
        return result


class ValidationWizard(models.TransientModel):
    _name = 'timesheet.validation'

    validation_date = fields.Date('Validate up to')
    validation_line_ids = fields.One2many('timesheet.validation.line', 'validation_id')

    def action_validate(self):
        self.validation_line_ids.filtered('validate').mapped('employee_id').write({'timesheet_validated': self.validation_date})
        return {'type': 'ir.actions.act_window_close'}


class ValidationWizardLine(models.TransientModel):
    _name = 'timesheet.validation.line'

    validation_id = fields.Many2one('timesheet.validation', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, ondelete='cascade')
    validate = fields.Boolean(
        default=True, help="Validate this employee's timesheet up to the chosen date")
