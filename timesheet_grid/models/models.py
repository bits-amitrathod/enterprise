# -*- coding: utf-8 -*-

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.addons.web_grid.models import END_OF, STEP_BY, START_OF
from odoo.exceptions import UserError
from odoo.osv import expression


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
