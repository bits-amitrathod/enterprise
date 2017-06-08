# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

from odoo.addons.timesheet_grid_sale.models.sale import DEFAULT_INVOICED_TIMESHEET


class TimesheetConfiguration(models.TransientModel):
    _inherit = 'hr.timesheet.config.settings'

    invoiced_timesheet = fields.Selection([
        ('all', "Invoice all recorded timesheets"),
        ('approved', "Invoice approved timesheets only"),
    ], default='all', string="Timesheets Invoicing")

    @api.multi
    def set_default_invoiced_timesheet(self):
        for record in self:
            self.env['ir.config_parameter'].sudo().set_param(
                'sale.invoiced_timesheet',
                record.invoiced_timesheet
            )
        return True

    @api.model
    def get_default_invoiced_timesheet(self, fields):
        result = self.env['ir.config_parameter'].sudo().get_param('sale.invoiced_timesheet', DEFAULT_INVOICED_TIMESHEET)
        return {'invoiced_timesheet': result}


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    invoiced_timesheet = fields.Selection([
        ('all', "Invoice all recorded timesheets"),
        ('approved', "Invoice approved timesheets only"),
    ], default='all', string="Timesheets Invoicing")

    @api.multi
    def set_default_invoiced_timesheet(self):
        for record in self:
            self.env['ir.config_parameter'].set_param(
                'sale.invoiced_timesheet',
                record.invoiced_timesheet
            )
        return True

    @api.model
    def get_default_invoiced_timesheet(self, fields):
        result = self.env['ir.config_parameter'].get_param('sale.invoiced_timesheet', DEFAULT_INVOICED_TIMESHEET)
        return {'invoiced_timesheet': result}
