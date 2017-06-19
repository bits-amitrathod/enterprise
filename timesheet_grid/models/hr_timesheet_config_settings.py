# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrTimesheetConfigSettings(models.TransientModel):

    _inherit = 'hr.timesheet.config.settings'

    reminder_user_allow = fields.Boolean("User Reminder",
        help="If checked, send an email to all users who have not recorded their timesheet")
    reminder_user_delay = fields.Integer("Number of days")
    reminder_user_interval = fields.Selection([
        ('weeks', 'After end of week'),
        ('months', 'After end of month')
    ], string='Frequency', required=True)

    reminder_manager_allow = fields.Boolean("Manager Reminder",
        help="If checked, send an email to all manager")
    reminder_manager_delay = fields.Integer("Number of days")
    reminder_manager_interval = fields.Selection([
        ('weeks', 'After end of week'),
        ('months', 'After end of month')
    ], string='Frequency', required=True)

    @api.model
    def get_values(self):
        res = super(HrTimesheetConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        cron_user = self.env.ref('timesheet_grid.timesheet_reminder_user')
        cron_manager = self.env.ref('timesheet_grid.timesheet_reminder_manager')
        res.update(
            reminder_user_allow=cron_user.active,
            reminder_user_delay=int(params.get_param('timesheet.reminder.user.delay', '0')),
            reminder_user_interval=cron_user.interval_type,
            reminder_manager_allow=cron_manager.active,
            reminder_manager_delay=int(params.get_param('timesheet.reminder.manager.delay', '0')),
            reminder_manager_interval=cron_manager.interval_type,
        )
        return res

    def set_values(self):
        super(HrTimesheetConfigSettings, self).set_values()
        self.env.ref('timesheet_grid.timesheet_reminder_user').write({'active': self.reminder_user_allow})
        self.env['ir.config_parameter'].sudo().set_param('timesheet.reminder.user.delay', self.reminder_user_delay)
        self._set_cron_next_execution_date('timesheet_grid.timesheet_reminder_user', self.reminder_user_interval, self.reminder_user_delay)
        self.env.ref('timesheet_grid.timesheet_reminder_manager').write({'active': self.reminder_manager_allow})
        self.env['ir.config_parameter'].sudo().set_param('timesheet.reminder.manager.delay', self.reminder_manager_delay)
        self._set_cron_next_execution_date('timesheet_grid.timesheet_reminder_manager', self.reminder_manager_interval, self.reminder_manager_delay)

    def _set_cron_next_execution_date(self, xml_id, frequency, delay=0):
        now = datetime.now()
        # end of previous week or month
        end_period = now - timedelta(days=now.weekday()+1)
        if frequency == 'months':
            end_period = now + relativedelta(day=31) - relativedelta(months=1)
        # add delay
        nextcall = end_period + relativedelta(days=delay)
        # set the nextcall in the future, if it is already passed
        if nextcall <= now:
            offset = relativedelta(months=1) if frequency == 'months' else relativedelta(weeks=1)
            nextcall += offset
        # write the date
        cron = self.env.ref(xml_id)
        if cron:
            cron.write({
                'interval_type': frequency,
                'nextcall': fields.Datetime.to_string(nextcall),
            })
        return nextcall
