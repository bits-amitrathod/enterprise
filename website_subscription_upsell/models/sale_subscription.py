# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleSubscription(models.Model):
    _inherit = "sale.subscription"

    def set_option(self, subscription, new_option, price):
        res = super(SaleSubscription, self).set_option(subscription, new_option, price)
        if not price or not price * subscription.partial_recurring_invoice_ratio() or not subscription.template_id.partial_invoice:
            subscription.sudo().add_option(new_option.id)
            msg_body = self.env['ir.ui.view'].render_template('website_subscription.chatter_add_option',
                                                                 values={'new_option': new_option, 'price': price})
            subscription.message_post(body=msg_body)
        return res

    def partial_invoice_line(self, sale_order, option_line, refund=False, date_from=False):
        new_order_line = super(SaleSubscription, self).partial_invoice_line(sale_order, option_line, refund, date_from)
        new_order_line.write({'force_price': True})
        return new_order_line

class SaleSubscriptionTemplate(models.Model):
    _inherit = "sale.subscription.template"

    partial_invoice = fields.Boolean(string="Pro-rated Upsell", help="If set, option upgrades must be paid for remainder of the current invoicing period.")
