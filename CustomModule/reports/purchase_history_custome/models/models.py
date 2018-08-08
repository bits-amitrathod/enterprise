# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class purchase_history(models.TransientModel):
    _name = 'purchase.history.cust'

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date(string="End Date", required=True)
    product_id = fields.Many2one('product.product', string="Products")

    @api.multi
    def get_report_values(self):
        pId = self.product_id.id
        _logger.info('AKASH %r', pId)
        purchase_orders = self.env['purchase.order.line'].search([('product_id', '=', self.product_id.id)])
        _logger.info('AKASH %r', pId)
        groupby_dict = {}
        filtered_by_date = list(
            filter(lambda x: x.date_order >= self.start_date and x.date_order <= self.end_date, purchase_orders))
        groupby_dict['data'] = filtered_by_date

        productProduct = self.env['product.product'].search([('product_tmpl_id','=',self.product_id.product_tmpl_id.id)])

        productMaxMinDates = {}
        for val in productProduct:
            val.env.cr.execute(
                "SELECT min(use_date), max (use_date) FROM public.stock_production_lot where product_id = %d" % self.product_id.id)
            query_result = val.env.cr.dictfetchone()

        final_dict = {}
        for user in groupby_dict.keys():
            temp = []
            for order in groupby_dict[user]:
                temp_2 = []

                temp_2.append(order.partner_id.name)
                temp_2.append(order.name)
                temp_2.append(order.price_total)
                temp_2.append(order.order_id.name)
                temp_2.append(order.product_qty)
                temp_2.append(order.product_id.product_tmpl_id.manufacturer.name)
                temp_2.append(order.product_id.product_tmpl_id.list_price)
                temp_2.append(order.product_id.default_code)
                temp_2.append(order.qty_received)
                temp_2.append(order.product_id.product_tmpl_id.description)
                temp_2.append(query_result['min'])
                temp_2.append(query_result['max'])

                temp.append(temp_2)
            final_dict[user] = temp
        datas = {
            'ids': self,
            'model': 'purchase.history.cust',
            'form': final_dict,
            'start_date': self.start_date,
            'end_date': self.end_date,

        }
        return self.env.ref('purchase_history_custome.action_todo_model_report').report_action([],
                                                                                               data=datas)

