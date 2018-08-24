# -*- coding: utf-8 -*-
##############################################################################
#
#    This module uses OpenERP, Open Source Management Solution Framework.
#    Copyright (C) 2017-Today Sitaram
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from odoo import api, fields, models
from odoo.tools import float_repr
import datetime
import logging


class SaleSalespersonReport(models.TransientModel):
    _name = 'sale.productbymonth.report'

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date(string="End Date", required=True)
    product_id = fields.Many2many('product.product', string="Products")

    @api.model
    def check(self, data):
        if data:
            return data
        else:
            return " "

    @api.multi
    def print_salesbymonth_vise_report(self):
        sale_orders = self.env['sale.order'].search([])
        groupby_dict = {}
        # for user in self.product_id:
            # filtered_order = list(filter(lambda x: x.product_id == user, sale_orders))
        filtered_by_date = list(
                filter(lambda x: x.date_order >= self.start_date and x.date_order <= self.end_date, sale_orders))
        groupby_dict['data'] = filtered_by_date

        final_dict = {}
        for user in groupby_dict.keys():
            temp = []
            for order in groupby_dict[user]:
                temp_2 = []
                temp_2.append(order.product_id.product_tmpl_id.sku_code)
                temp_2.append(order.product_id.name)
                temp_2.append(float_repr(order.amount_total,precision_digits=2))
                temp_2.append(fields.Datetime.from_string(str(order.date_order)).date().strftime('%m/%d/%Y'))
                temp_2.append(order.name)

                temp.append(temp_2)
            final_dict[user] = temp
            final_dict['data'].sort(key=lambda x: self.check(x[4]))
        datas = {
            'ids': self,
            'model': 'sale.product.report',
            'form': final_dict,
            'start_date': fields.Datetime.from_string(str(self.start_date)).date().strftime('%m/%d/%Y'),
            'end_date': fields.Datetime.from_string(str(self.end_date)).date().strftime('%m/%d/%Y'),

        }
        return self.env.ref('sr_sales_report_product_bymonth.action_report_sales_salesbymonth_wise').report_action([],
                                                                                                                    data=datas)

