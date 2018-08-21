# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import datetime

_logger = logging.getLogger(__name__)
class lot_history(models.TransientModel):
    _name = 'lot_history.lot_history'

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date(string="End Date", required=True)
    product_id = fields.Many2one('product.product', string="Products", required=True)

    @api.multi
    def get_report_values(self):
        lots = self.env['stock.production.lot'].search([])
        groupby_dict = {}
        filtered_order = lots
        filtered_by_date = filtered_order
        groupby_dict['data'] = filtered_by_date

        final_dict = {}
        for user in groupby_dict.keys():
            temp = []
            for order in groupby_dict[user]:
                temp_2 = []
                temp_2.append(order.name)
                temp_2.append(order.product_id.product_tmpl_id.name)
                temp_2.append(order.product_id.product_tmpl_id.description)
                temp_2.append(order.product_id.product_tmpl_id.type)
                temp_2.append(order.product_id.product_tmpl_id.manufacturer.display_name)
                temp_2.append(order.product_id.product_tmpl_id.manufacturer.email)
                temp_2.append(order.product_id.product_tmpl_id.manufacturer.phone)
                temp_2.append(datetime.datetime.strptime(str(order.create_date),'%Y-%m-%d %H:%M:%S').date().strftime( '%d-%m-%Y'))
                temp.append(temp_2)
            final_dict[user] = temp

        datas = {
            'ids': self,
            'model': 'product.list.report',
            'form': final_dict,
            'start_date': self.start_date,
            'end_date': self.end_date,

        }
        return self.env.ref('lot_history.action_todo_model_report').report_action([], data=datas)
