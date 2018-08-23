# -*- coding: utf-8 -*-
from odoo import http


class WebsiteCstm(http.Controller):
    @http.route('/', type='http', auth="public", website=True)
    def home(self, **kw):
        return http.request.render('website_cstm.home')

    @http.route('/contactus', type='http', auth="public", website=True)
    def contact(self):
        return http.request.render('website_cstm.contact_page')

    @http.route('/about', type='http', auth="public", website=True)
    def about(self):
        return http.request.render('website_cstm.about_page')

    @http.route('/faqs', type='http', auth="public", website=True)
    def faqs(self):
        return http.request.render('website_cstm.faqs_page')

    @http.route('/quality_assurance', type='http', auth="public", website=True)
    def quality_assurance_page(self):
        return http.request.render('website_cstm.quality_assurance_page')

    @http.route('/vendors', type='http', auth="public", website=True)
    def vendors_page(self):
        return http.request.render('website_cstm.vendors_page')

    @http.route('/product_types', type='http', auth="public", website=True)
    def product_types_page(self):
        return http.request.render('website_cstm.product_types_page')