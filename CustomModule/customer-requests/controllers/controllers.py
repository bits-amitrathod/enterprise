# -*- coding: utf-8 -*-
from odoo import http

# class Customer-requests(http.Controller):
#     @http.route('/customer-requests/customer-requests/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/customer-requests/customer-requests/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('customer-requests.listing', {
#             'root': '/customer-requests/customer-requests',
#             'objects': http.request.env['customer-requests.customer-requests'].search([]),
#         })

#     @http.route('/customer-requests/customer-requests/objects/<model("customer-requests.customer-requests"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('customer-requests.object', {
#             'object': obj
#         })