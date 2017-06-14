# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, exceptions, fields, models, _

from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class Project(models.Model):
    _inherit = 'project.project'

    allow_forecast = fields.Boolean("Allow forecast", default=False, help="This feature shows the Forecast link in the kanban view")

    @api.multi
    def write(self, vals):
        if 'active' in vals:
            self.env['project.forecast'].with_context(active_test=False).search([('project_id', 'in', self.ids)]).write({'active': vals['active']})
        return super(Project, self).write(vals)

    @api.multi
    def unlink(self):
        if self.env['project.forecast'].search([('project_id', 'in', self.ids)]):
            raise UserError(_('You cannot delete a project containing forecasts. You can either delete all the project\'s forecasts and then delete the project or simply deactivate the project.'))
        return super(Project, self).unlink()

    def action_view_project_forecast(self):
        action = self.env.ref('project_forecast.project_forecast_action_from_project').read()[0]
        context = {}
        if action.get('context'):
            eval_context = self.env['ir.actions.actions']._get_eval_context()
            eval_context.update({'active_id': self.id})
            context = safe_eval(action['context'], eval_context)
        # add the default employee (for creation)
        context['default_employee_id'] = self.user_id.employee_ids[:1].id
        action['context'] = context
        return action


class Task(models.Model):
    _inherit = 'project.task'

    allow_forecast = fields.Boolean('Allow Forecast', readonly=True, related='project_id.allow_forecast', store=False)

    @api.multi
    def write(self, vals):
        if 'active' in vals:
            self.env['project.forecast'].with_context(active_test=False).search([('task_id', 'in', self.ids)]).write({'active': vals['active']})
        return super(Task, self).write(vals)

    @api.multi
    def unlink(self):
        if self.env['project.forecast'].search([('task_id', 'in', self.ids)]):
            raise UserError(_('You cannot delete a task containing forecasts. You can either delete all the task\'s forecasts and then delete the task or simply deactivate the task.'))
        return super(Task, self).unlink()
