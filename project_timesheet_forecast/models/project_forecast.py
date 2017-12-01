# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo import api, fields, models


class Forecast(models.Model):

    _inherit = "project.forecast"

    working_days_count = fields.Integer("Number of working days", compute='_compute_working_days_count', store=True)

    # TODO JEM: should be moved to project_forecast and mixed with compute_time (see master-forecast-poc2-jem)
    @api.multi
    @api.depends('employee_id', 'employee_id.resource_calendar_id', 'start_date', 'end_date')
    def _compute_working_days_count(self):
        for forecast in self:
            start_dt = datetime.datetime.combine(fields.Datetime.from_string(forecast.start_date), datetime.time.min)
            stop_dt = datetime.datetime.combine(fields.Datetime.from_string(forecast.end_date), datetime.time.max)
            forecast.working_days_count = forecast.employee_id.get_work_days_data(start_dt, stop_dt)['days']
