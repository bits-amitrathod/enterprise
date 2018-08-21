# -*- coding: utf-8 -*-
from odoo import http
# class BitsStockProduction(http.Controller):
#     @http.route('/bits_stock_production/bits_stock_production/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/bits_stock_production/bits_stock_production/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('bits_stock_production.listing', {
#             'root': '/bits_stock_production/bits_stock_production',
#             'objects': http.request.env['bits_stock_production.bits_stock_production'].search([]),
#         })

#     @http.route('/bits_stock_production/bits_stock_production/objects/<model("bits_stock_production.bits_stock_production"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('bits_stock_production.object', {
#             'object': obj
#         })