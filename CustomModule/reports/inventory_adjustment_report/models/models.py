# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class inventory_adjustment_report(models.TransientModel):
    _name = 'inventory.adjustment.report'

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date(string="End Date", required=True)



    @api.multi
    def get_report_values(self):
        adjustment = self.env['stock.inventory.line'].search([])
        _logger.info('AKASH %r', adjustment)
        groupby_dict = {}
        filtered_by_date = list(
            filter(lambda x: x.inventory_id.date >= self.start_date and x.inventory_id.date <= self.end_date, adjustment))
        _logger.info('AKASH %r', filtered_by_date)
        groupby_dict['data'] = filtered_by_date
        final_dict = {}
        for user in groupby_dict.keys():
            temp = []
            for order in groupby_dict[user]:
                temp_2 = []
                temp_2.append(order.product_name)
                temp_2.append(order.create_date)
                temp_2.append(order.product_code)
                temp_2.append(order.product_qty)
                temp_2.append(order.product_id.product_tmpl_id.list_price)
                temp_2.append(order.product_qty*order.product_id.product_tmpl_id.list_price)

                temp.append(temp_2)
            final_dict[user] = temp
        datas = {
            'ids': self,
            'model': 'inventory.adjustment.report',
            'form': final_dict,
            'start_date': self.start_date,
            'end_date': self.end_date,

        }
        return self.env.ref('inventory_adjustment_report.action_todo_model_report').report_action([],
                                                                                               data=datas)

