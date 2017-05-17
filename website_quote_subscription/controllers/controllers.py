# -*- coding: utf-8 -*-
from odoo import http

# class WebsiteQuoteSubscription(http.Controller):
#     @http.route('/website_quote_subscription/website_quote_subscription/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/website_quote_subscription/website_quote_subscription/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('website_quote_subscription.listing', {
#             'root': '/website_quote_subscription/website_quote_subscription',
#             'objects': http.request.env['website_quote_subscription.website_quote_subscription'].search([]),
#         })

#     @http.route('/website_quote_subscription/website_quote_subscription/objects/<model("website_quote_subscription.website_quote_subscription"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('website_quote_subscription.object', {
#             'object': obj
#         })