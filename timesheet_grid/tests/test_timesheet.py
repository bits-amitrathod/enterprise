# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields

from odoo.addons.web_grid.models import END_OF
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestTimesheet(TransactionCase):

    def setUp(self):
        super(TestTimesheet, self).setUp()

        self.project_customer = self.env['project.project'].create({
            'name': 'Project X',
            'allow_timesheets': True,
            'use_tasks': True,
        })
        self.task1 = self.env['project.task'].create({
            'name': 'Task One',
            'priority': '0',
            'kanban_state': 'normal',
            'project_id': self.project_customer.id,
        })
        self.task2 = self.env['project.task'].create({
            'name': 'Task Two',
            'priority': '1',
            'kanban_state': 'done',
            'project_id': self.project_customer.id,
        })
        # users
        self.user_employee = self.env['res.users'].create({
            'name': 'User Employee',
            'login': 'user_employee',
            'groups_id': [(4, self.ref('hr_timesheet.group_hr_timesheet_user'))],
        })
        self.user_manager = self.env['res.users'].create({
            'name': 'User Officer',
            'login': 'user_manager',
            'groups_id': [(4, self.ref('hr_timesheet.group_timesheet_manager'))],
        })
        # employees
        self.empl_employee = self.env['hr.employee'].create({
            'name': 'User Empl Employee',
            'user_id': self.user_employee.id,
        })
        self.empl_manager = self.env['hr.employee'].create({
            'name': 'User Empl Officer',
            'user_id': self.user_manager.id,
        })
        # timesheets
        today = fields.Date.today()
        self.timesheet1 = self.env['account.analytic.line'].sudo(self.user_employee.id).create({
            'name': "my timesheet 1",
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'date': today,
            'unit_amount': 2.0,
        })
        self.timesheet2 = self.env['account.analytic.line'].sudo(self.user_employee.id).create({
            'name': "my timesheet 2",
            'project_id': self.project_customer.id,
            'task_id': self.task2.id,
            'date': today,
            'unit_amount': 3.11,
        })

    def test_timesheet_validation_user(self):
        """ Employee record its timesheets and Officer validate them. Then try to modify/delete it and get Access Error """
        # Officer validate timesheet of 'user_employee' through wizard
        timesheet_to_validate = self.timesheet1 | self.timesheet2
        validate_action = timesheet_to_validate.sudo(self.user_manager).action_validate_timesheet()
        wizard = self.env['timesheet.validation'].browse(validate_action['res_id'])
        wizard.action_validate()

        # Check validated date
        end_of_week = fields.Date.to_string(datetime.now() + END_OF['week'])
        self.assertEquals(self.empl_employee.timesheet_validated, end_of_week, 'validate timesheet date should be the end of the week')

        # Employee can not modify validated timesheet
        with self.assertRaises(AccessError):
            self.timesheet1.sudo(self.user_employee.id).write({'unit_amount': 5})
        # Employee can not delete validated timesheet
        with self.assertRaises(AccessError):
            self.timesheet2.sudo(self.user_employee.id).unlink()
        # Employee can not create new timesheet in the validated period
        with self.assertRaises(AccessError):
            last_month = fields.Date.to_string(datetime.now() - relativedelta(months=1))
            self.env['account.analytic.line'].sudo(self.user_employee.id).create({
                'name': "my timesheet 3",
                'project_id': self.project_customer.id,
                'task_id': self.task2.id,
                'date': last_month,
                'unit_amount': 2.5,
            })

        # Employee can still create timesheet after validated date
        next_month = fields.Date.to_string(datetime.now() + relativedelta(months=1))
        timesheet4 = self.env['account.analytic.line'].sudo(self.user_employee.id).create({
            'name': "my timesheet 4",
            'project_id': self.project_customer.id,
            'task_id': self.task2.id,
            'date': next_month,
            'unit_amount': 2.5,
        })
        # And can still update non validated timesheet
        timesheet4.write({'unit_amount': 7})

    def test_timesheet_validation_manager(self):
        """ Officer can see timesheets and modify the ones of other employees """
       # Officer validate timesheet of 'user_employee' through wizard
        timesheet_to_validate = self.timesheet1 | self.timesheet2
        validate_action = timesheet_to_validate.sudo(self.user_manager.id).action_validate_timesheet()
        wizard = self.env['timesheet.validation'].browse(validate_action['res_id'])
        wizard.action_validate()

        # manager modify validated timesheet
        self.timesheet1.sudo(self.user_manager.id).write({'unit_amount': 5})
