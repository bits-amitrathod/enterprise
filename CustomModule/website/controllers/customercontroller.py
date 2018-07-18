from odoo import http


class MyFirstModel(http.Controller):

    @http.route('/home', type='http', auth="public", website=True)
    def home(self):
        customer = http.request.env['customer'].sudo().search([])
        return http.request.render('website.home_page', {'customers': customer})

    @http.route('/catalog', type='http', auth="public", website=True)
    def catalog(self):
        cat = http.request.env['customer'].sudo().search([])
        return http.request.render('website.catalog_page', {'customers': cat})

    @http.route('/feature', type='http', auth="public", website=True)
    def feature(self):
        featureproduct = http.request.env['customer'].sudo().search([])
        return http.request.render('website.featureproducts_page', {'customers': featureproduct})

    @http.route('/about', type='http', auth="public", website=True)
    def about(self):
        about = http.request.env['customer'].sudo().search([])
        return http.request.render('website.about_page', {'customers': about})

    @http.route('/faqs1', type='http', auth="public", website=True)
    def faqs(self):
        faqs = http.request.env['customer'].sudo().search([])
        return http.request.render('website.faqs_page', {'customers': faqs})

    @http.route('/contact1', type='http', auth="public", website=True)
    def contact(self):
        contact = http.request.env['customer'].sudo().search([])
        return http.request.render('website.contact_page', {'customers': contact})

    @http.route('/product', type='http', auth="public", website=True)
    def product(self):
        product = http.request.env['customer'].sudo().search([])
        return http.request.render('website.productdetails_page', {'customers': product})

