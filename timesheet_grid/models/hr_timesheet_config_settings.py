# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class TimesheetConfig(models.TransientModel):

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

    # Cron for users

    @api.model
    def get_default_reminder_user_allow(self, _fields):
        cron = self.env.ref('timesheet_grid.timesheet_reminder_user')
        return {
            'reminder_user_allow': cron.active
        }

    @api.multi
    def set_reminder_user_allow(self):
        self.ensure_one()
        cron = self.env.ref('timesheet_grid.timesheet_reminder_user')
        cron.write({'active': self.reminder_user_allow})

    @api.model
    def get_default_reminder_user_delay(self, _fields):
        return {
            'reminder_user_delay': int(self.env['ir.config_parameter'].sudo().get_param('timesheet.reminder.user.delay', '0'))
        }

    @api.multi
    def set_reminder_user_delay(self):
        if self.reminder_user_delay:
            self.env['ir.config_parameter'].sudo().set_param('timesheet.reminder.user.delay', self.reminder_user_delay)
            self._set_cron_next_execution_date('timesheet_grid.timesheet_reminder_user', self.reminder_user_interval, self.reminder_user_delay)

    @api.model
    def get_default_reminder_user_interval(self, _fields):
        cron = self.env.ref('timesheet_grid.timesheet_reminder_user')
        return {
            'reminder_user_interval': cron.interval_type
        }

    @api.multi
    def set_reminder_user_interval(self):
        self.ensure_one()
        self._set_cron_next_execution_date('timesheet_grid.timesheet_reminder_user', self.reminder_user_interval, self.reminder_user_delay)

    # Cron for manager

    @api.model
    def get_default_reminder_manager_allow(self, _fields):
        cron = self.env.ref('timesheet_grid.timesheet_reminder_manager')
        return {
            'reminder_manager_allow': cron.active
        }

    @api.multi
    def set_reminder_manager_allow(self):
        self.ensure_one()
        cron = self.env.ref('timesheet_grid.timesheet_reminder_manager')
        cron.write({'active': self.reminder_manager_allow})

    @api.model
    def get_default_reminder_manager_delay(self, _fields):
        return {
            'reminder_manager_delay': int(self.env['ir.config_parameter'].sudo().get_param('timesheet.reminder.manager.delay', '0'))
        }

    @api.multi
    def set_reminder_manager_delay(self):
        if self.reminder_manager_delay:
            self.env['ir.config_parameter'].sudo().set_param('timesheet.reminder.manager.delay', self.reminder_manager_delay)
            self._set_cron_next_execution_date('timesheet_grid.timesheet_reminder_manager', self.reminder_manager_interval, self.reminder_manager_delay)

    @api.model
    def get_default_reminder_manager_interval(self, _fields):
        cron = self.env.ref('timesheet_grid.timesheet_reminder_manager')
        return {
            'reminder_manager_interval': cron.interval_type
        }

    @api.multi
    def set_reminder_manager_interval(self):
        self.ensure_one()
        self._set_cron_next_execution_date('timesheet_grid.timesheet_reminder_manager', self.reminder_manager_interval, self.reminder_manager_delay)

    # Common / others

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
