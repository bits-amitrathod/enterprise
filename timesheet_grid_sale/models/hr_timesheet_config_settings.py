# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

from odoo.addons.timesheet_grid_sale.models.sale import DEFAULT_INVOICED_TIMESHEET


class HrTimesheetConfigSettings(models.TransientModel):
    _inherit = 'hr.timesheet.config.settings'

    invoiced_timesheet = fields.Selection([
        ('all', "Invoice all recorded timesheets"),
        ('approved', "Invoice approved timesheets only"),
    ], default='all', string="Timesheets Invoicing")

    def set_values(self):
        super(HrTimesheetConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('sale.invoiced_timesheet', self.invoiced_timesheet)

    @api.model
    def get_values(self):
        res = super(HrTimesheetConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            invoiced_timesheet=params.get_param('sale.invoiced_timesheet', DEFAULT_INVOICED_TIMESHEET)
        )
        return res


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    invoiced_timesheet = fields.Selection([
        ('all', "Invoice all recorded timesheets"),
        ('approved', "Invoice approved timesheets only"),
    ], default='all', string="Timesheets Invoicing")

    def set_values(self):
        super(SaleConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param('sale.invoiced_timesheet',self.invoiced_timesheet)

    @api.model
    def get_values(self):
        res = super(SaleConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(invoiced_timesheet=params.get_param('sale.invoiced_timesheet', DEFAULT_INVOICED_TIMESHEET))
        return res
