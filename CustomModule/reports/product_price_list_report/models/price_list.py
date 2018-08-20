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



class SaleSalespersonReport(models.TransientModel):
    _name = 'product.list.report'

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date(string="End Date", required=True)
    user_ids = fields.Many2many('res.users', string="Salesperson")

    @api.multi
    def print_product_price_list_vise_report(self):
        sale_orders = self.env['product.template'].search([])
        groupby_dict = {}
        filtered_order = sale_orders
        filtered_by_date = filtered_order
        groupby_dict['data'] = filtered_by_date

        final_dict = {}
        for user in groupby_dict.keys():
            temp = []
            for order in groupby_dict[user]:
                temp_2 = []
                temp_2.append(order.default_code)
                temp_2.append(order.description)
                temp_2.append(order.standard_price)
                temp.append(temp_2)
            final_dict[user] = temp

        datas = {
            'ids': self,
            'model': 'product.list.report',
            'form': final_dict,
            'start_date': self.start_date,
            'end_date': self.end_date,

        }
        return self.env.ref('product_price_list_report.action_report_price_list_wise').report_action([], data=datas)
