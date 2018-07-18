from . import http

class MyFirstModel(http.Controller):
    
@http.route('/home', type='http', auth="public", website=True)
def home(self):
customer = http.request.env['customer'].sudo().search([])
return http.request.render('website.home', {'customers': customer})