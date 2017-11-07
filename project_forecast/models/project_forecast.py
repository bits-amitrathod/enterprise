# -*- coding: utf-8 -*-

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta, MO, SU

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
from odoo.tools import float_round
from odoo.osv import expression
from odoo.tools import pycompat

from odoo.addons.resource.models.resource import HOURS_PER_DAY


class ProjectForecast(models.Model):
    _name = 'project.forecast'

    def _default_employee_id(self):
        user_id = self.env.context.get('default_user_id', self.env.uid)
        employee_ids = self.env['hr.employee'].search([('user_id', '=', user_id)])
        return employee_ids and employee_ids[0] or False

    def _default_start_date(self):
        forecast_span = self.env.user.company_id.forecast_span
        start_date = date.today()
        # grid context: default start date should be the one of the first grid column
        if self._context.get('grid_anchor'):
            start_date = fields.Date.from_string(self._context['grid_anchor'])

        if forecast_span == 'week':
            start_date += relativedelta(weekday=MO(-1))  # beginning of current week
        elif forecast_span == 'month':
            start_date += relativedelta(day=1)  # beginning of current month
        return fields.Date.to_string(start_date)

    def _default_end_date(self):
        forecast_span = self.env.user.company_id.forecast_span

        start_date = self._default_start_date()
        if 'default_start_date' in self._context:
            start_date = self._context.get('default_start_date')
        start_date = fields.Date.from_string(start_date)

        delta = relativedelta()
        if forecast_span == 'week':
            delta = relativedelta(weekday=SU)  # end of current week
        elif forecast_span == 'month':
            delta = relativedelta(months=1, day=1, days=-1)  # end of current month
        return fields.Date.to_string(start_date + delta)

    def _read_group_employee_ids(self, employee, domain, order):
        group = self.env.ref('project.group_project_user', False) or self.env.ref('base.group_user')
        return self.env['hr.employee'].search([('user_id', 'in', group.users.ids)])

    name = fields.Char(compute='_compute_name')
    active = fields.Boolean(default=True)
    employee_id = fields.Many2one('hr.employee', "Employee", default=_default_employee_id, required=True, group_expand='_read_group_employee_ids')
    user_id = fields.Many2one('res.users', string="User", related='employee_id.user_id', store=True, readonly=True)
    project_id = fields.Many2one('project.project', string="Project", required=True)
    task_id = fields.Many2one(
        'project.task', string="Task", domain="[('project_id', '=', project_id)]",
        group_expand='_read_forecast_tasks')
    company_id = fields.Many2one('res.company', string="Company", related='project_id.company_id', store=True, readonly=True)

    # used in custom filter
    stage_id = fields.Many2one(related='task_id.stage_id', string="Task stage")
    tag_ids = fields.Many2many(related='task_id.tag_ids', string="Task tags")

    time = fields.Float(string="%", help="Percentage of working time", compute='_compute_time', store=True, digits=(16, 2))

    start_date = fields.Date(default=_default_start_date, required=True)
    end_date = fields.Date(default=_default_end_date, required=True)
    # consolidation color and exclude
    color = fields.Integer(string="Color", compute='_compute_color')
    exclude = fields.Boolean(string="Exclude", compute='_compute_exclude', store=True)

    # resource
    resource_hours = fields.Float(string="Planned hours", default=0)
    resource_time = fields.Float("Allocated Time", compute='_compute_resource_time', inverse='_inverse_resource_time', store=True, help="Expressed in the Unit of Measure of the project company")
    forecast_uom = fields.Selection(related='company_id.forecast_uom')

    _sql_constraints = [
        ('check_start_date_lower_end_date', 'CHECK(end_date >= start_date)', 'Forecast end date should be greater or equal to its start date'),
    ]

    @api.one
    @api.depends('project_id', 'task_id', 'employee_id')
    def _compute_name(self):
        group = self.env.context.get("group_by", "")

        name = []
        if "employee_id" not in group:
            name.append(self.employee_id.name)
        if ("project_id" not in group):
            name.append(self.project_id.name)
        if ("task_id" not in group and self.task_id):
            name.append(self.task_id.name)

        if name:
            self.name = " - ".join(name)
        else:
            self.name = _("undefined")

    @api.one
    @api.depends('project_id.color')
    def _compute_color(self):
        self.color = self.project_id.color or 0

    @api.one
    @api.depends('project_id.name')
    def _compute_exclude(self):
        self.exclude = (self.project_id.name == "Leaves")

    @api.one
    @api.depends('resource_hours', 'start_date', 'end_date', 'employee_id')
    def _compute_time(self):
        start = fields.Datetime.from_string(self.start_date)
        stop = fields.Datetime.from_string(self.end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
        hours = self.employee_id.resource_calendar_id.get_work_hours_count(start, stop, False, compute_leaves=False)
        if hours > 0:
            self.time = self.resource_hours * 100.0 / hours
        else:
            self.time = 0  # allow to create a forecast for a day you are not supposed to work

    @api.multi
    @api.depends('resource_hours', 'company_id.forecast_uom', 'project_id.resource_calendar_id')
    def _compute_resource_time(self):
        for forecast in self:
            factor = 1.0
            if forecast.company_id.forecast_uom == 'day':
                calendar = forecast.project_id.resource_calendar_id or forecast.company_id.resource_calendar_id
                factor = calendar.hours_per_day if calendar else HOURS_PER_DAY
            forecast.resource_time = float_round(forecast.resource_hours / factor, precision_digits=2)

    @api.multi
    def _inverse_resource_time(self):
        for forecast in self:
            factor = 1.0
            if forecast.company_id.forecast_uom == 'day':
                calendar = forecast.project_id.resource_calendar_id or forecast.company_id.resource_calendar_id
                factor = calendar.hours_per_day if calendar else HOURS_PER_DAY
            forecast.resource_hours = float_round(forecast.resource_time * factor, precision_digits=2)

    @api.one
    @api.constrains('resource_hours')
    def _check_time_positive(self):
        if self.resource_hours and (self.resource_hours < 0):
            raise ValidationError(_("Forecasted time must be positive"))

    @api.one
    @api.constrains('task_id', 'project_id')
    def _check_task_in_project(self):
        if self.task_id and (self.task_id not in self.project_id.tasks):
            raise ValidationError(_("Your task is not in the selected project."))

    @api.constrains('start_date', 'end_date', 'project_id', 'task_id', 'employee_id', 'active')
    def _check_overlap(self):
        self.env.cr.execute("""
            SELECT F1.id, F1.start_date, F1.end_date
            FROM project_forecast F1
            INNER JOIN project_forecast F2
                ON F1.employee_id = F2.employee_id AND F1.project_id = F2.project_id
            WHERE F1.id != F2.id
                AND (F1.task_id = F2.task_id OR (F1.task_id IS NULL AND F2.task_id IS NULL))
                AND (
                    F1.start_date BETWEEN F2.start_date AND F2.end_date
                    OR
                    F1.end_date BETWEEN F2.start_date AND F2.end_date
                    OR
                    F2.start_date BETWEEN F1.start_date AND F1.end_date
                )
                AND F1.active = 't'
                AND F1.id IN %s
        """, (tuple(self.ids),))
        if self.env.cr.fetchall():
            raise ValidationError(_('Forecast should not overlap existing forecasts.'))

    @api.onchange('task_id')
    def _onchange_task_id(self):
        if self.task_id:
            self.project_id = self.task_id.project_id

    @api.onchange('project_id')
    def _onchange_project_id(self):
        domain = [] if not self.project_id else [('project_id', '=', self.project_id.id)]
        return {
            'domain': {'task_id': domain},
        }

    @api.onchange('start_date')
    def _onchange_start_date(self):
        self.end_date = self.with_context(default_start_date=self.start_date)._default_end_date()

    # ----------------------------------------------------
    # Actions
    # ----------------------------------------------------

    @api.model
    def action_view_forecast(self, action_xmlid=None):
        """ This method extends the context of action defined in xml files to
            customize it according to the forecast span of the current company.

            :param action_xmlid: complete xml id of the action to return
            :returns action (dict): an action with a extended context, evaluable
                by the webclient
        """
        if not action_xmlid:
            action_xmlid = 'project_forecast.project_forecast_action_from_project'

        action = self.env.ref(action_xmlid).read()[0]
        context = {}
        if action.get('context'):
            eval_context = self.env['ir.actions.actions']._get_eval_context()
            if 'active_id' in self._context:
                eval_context.update({'active_id': self._context.get('active_id')})
            context = safe_eval(action['context'], eval_context)
        # add the default employee (for creation)
        context['default_employee_id'] = self.env.user.employee_ids[0].id
        # hide range button for grid view
        company = self.company_id or self.env.user.company_id
        if company.forecast_span == 'day':
            context['forecast_hide_range_month'] = True
            context['forecast_hide_range_year'] = True
        elif company.forecast_span == 'week':
            context['forecast_hide_range_week'] = True
            context['forecast_hide_range_year'] = True
        elif company.forecast_span == 'month':
            context['forecast_hide_range_week'] = True
            context['forecast_hide_range_month'] = True

        action['context'] = context
        return action

    # ----------------------------------------------------
    # Grid View Stuffs
    # ----------------------------------------------------

    def _grid_pagination(self, field, span, step, anchor):
        """ For forecast, we want the next and previous anchor date to be the border of the period, in order
            to se the default start_date value to match the beginning of the forecast span (of the company)
        """
        pagination = super(ProjectForecast, self)._grid_pagination(field, span, step, anchor)
        if field.type == 'date':
            for pagination_key in ['next', 'prev']:
                val = field.from_string(pagination[pagination_key]['default_%s' % field.name])
                pagination[pagination_key]['default_%s' % field.name] = field.to_string(self._grid_start_of(span, step, val))
        return pagination

    @api.multi
    def adjust_grid(self, row_domain, column_field, column_value, cell_field, change):
        if column_field != 'start_date' or cell_field != 'resource_time':
            raise exceptions.UserError(
                _("Grid adjustment for project forecasts only supports the "
                  "'start_date' columns field and the 'resource_time' cell "
                  "field, got respectively %(column_field)r and "
                  "%(cell_field)r") % {
                    'column_field': column_field,
                    'cell_field': cell_field,
                }
            )

        from_, to_ = pycompat.imap(fields.Date.from_string, column_value.split('/'))
        start = fields.Date.to_string(from_)
        # range is half-open get the actual end date
        end = fields.Date.to_string(to_ - relativedelta(days=1))

        # see if there is an exact match
        cell = self.search(expression.AND([row_domain, [
            '&',
            ['start_date', '=', start],
            ['end_date', '=', end]
        ]]), limit=1)
        # if so, adjust in-place
        if cell:
            cell[cell_field] += change
            return False

        # otherwise copy an existing cell from the row, ignore eventual
        # non-monthly forecast
        self.search(row_domain, limit=1).ensure_one().copy({
            'start_date': start,
            'end_date': end,
            cell_field: change,
        })
        return False

    # ----------------------------------------------------
    # Business Methods
    # ----------------------------------------------------

    @api.model
    def _read_forecast_tasks(self, tasks, domain, order):
        tasks_domain = [('id', 'in', tasks.ids)]
        if 'default_project_id' in self.env.context:
            tasks_domain = expression.OR([
                tasks_domain,
                [('project_id', '=', self.env.context['default_project_id'])]
            ])
        return tasks.sudo().search(tasks_domain, order=order)
