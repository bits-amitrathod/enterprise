# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class website_subscription_upsell(http.Controller):

    @http.route(['/my/subscription/<int:account_id>/pay_option'], type='http', methods=["POST"], auth="public", website=True)
    def pay_option(self, account_id, **kw):
        order = request.website.sale_get_order(force_create=True)
        order.set_project_id(account_id)
        new_option_id = int(kw.get('new_option_id'))
        new_option = request.env['sale.subscription.template.option'].sudo().browse(new_option_id)
        account = request.env['sale.subscription'].browse(account_id)
        account.sudo().partial_invoice_line(order, new_option)
        return request.redirect("/shop/cart")
