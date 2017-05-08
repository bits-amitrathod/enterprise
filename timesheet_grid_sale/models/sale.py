# -*- coding: utf-8 -*-
from odoo import api, models

DEFAULT_INVOICED_TIMESHEET = 'all'


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _compute_analytic(self, domain=None):
        param_invoiced_timesheet = self.env['ir.config_parameter'].sudo().get_param('sale.invoiced_timesheet', DEFAULT_INVOICED_TIMESHEET)
        if param_invoiced_timesheet == 'approved':
            domain = [
                    '&',
                        ('so_line', 'in', self.ids),
                        '|',
                            '&',
                            ('amount', '<=', 0.0),
                            ('is_timesheet', '=', False),
                            '&',
                                ('is_timesheet', '=', True),
                                ('validated', '=', True),
            ]

        return super(SaleOrderLine, self)._compute_analytic(domain=domain)
