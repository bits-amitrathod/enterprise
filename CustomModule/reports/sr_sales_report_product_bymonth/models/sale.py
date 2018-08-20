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
import datetime
import logging


class SaleSalespersonReport(models.TransientModel):
    _name = 'sale.productbymonth.report'

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date(string="End Date", required=True)
    product_id = fields.Many2many('product.product', string="Products")

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
                temp_2.append(order.name)
                temp_2.append(datetime.datetime.strptime(order.date_order, "%Y-%m-%d %H:%M:%S").date().strftime('%Y-%m-%d'))
                temp_2.append(order.amount_total)
                temp_2.append(order.product_id.name)
                temp.append(temp_2)
            final_dict[user] = temp
        datas = {
            'ids': self,
            'model': 'sale.product.report',
            'form': final_dict,
            'start_date': self.start_date,
            'end_date': self.end_date,

        }
        return self.env.ref('sr_sales_report_product_bymonth.action_report_sales_salesbymonth_wise').report_action([],
                                                                                                                    data=datas)

