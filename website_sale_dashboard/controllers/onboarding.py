from odoo import http
from odoo.http import request


class OnboardingController(http.Controller):

    @http.route('/website_sale_dashboard/website_sale_dashboard_onboarding', auth='user', type='json')
    def website_dashboard_onboarding(self):
        """ Returns the `banner` for the website sale onboarding panel.
            It can be empty if the user has closed it or if he doesn't have
            the permission to see it. """

        if not request.env.user._is_admin() or \
           request.env.user.company_id.website_sale_dashboard_onboarding_closed:
            return {}

        return {
            'html': request.env.ref('website_sale_dashboard.website_sale_dashboard_onboarding_panel').render({
                'company': request.env.user.company_id,
            })
        }
