# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"

    subscription_management = fields.Selection(string='Subscription Management', selection=[('create', 'Creation'), ('renew', 'Renewal'), ('upsell', 'Upselling')],
                                          help="Creation: The Sales Order created the subscription\n"
                                                "Upselling: The Sales Order added lines to the subscription\n"
                                                "Renewal: The Sales Order replaced the subscription's content with its own")
    subscription_count = fields.Integer(compute='_compute_subscription_count')

    def _compute_subscription_count(self):
        order_line_data = self.env['sale.order.line'].read_group([('subscription_id', '!=', False), ('order_id', 'in', self.ids)], ['subscription_id', 'order_id'], ['subscription_id', 'order_id'])
        subscription_count =  len([data['subscription_id'][0] for data in order_line_data])
        for order in self:
            order.subscription_count = subscription_count

    @api.multi
    def action_open_subscriptions(self):
        self.ensure_one()
        subscriptions = self.order_line.mapped('subscription_id')
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.subscription",
            "view_mode": 'tree,form',
            "domain": [["id", "in", subscriptions.ids]],
            "context": {"create": False},
            "name": _("Subscriptions"),
        }

    def create_subscription(self):
        """ Create a subscription based on the product's subscription template """
        templates = {}
        msg_template = self.env.ref('sale_subscription.chatter_add_paid_option')
        for order in self:
            values = {'recurring_invoice_line_ids': []}
            for line in order.order_line:
                if line.subscription_id:
                    # no need for updates if the subscription was juste created
                    # wipe the subscription clean if needed
                    if order.subscription_management == 'renew':
                        to_remove = [(2, subscription_line.id, 0) for subscription_line in line.subscription_id.recurring_invoice_line_ids]
                        line.subscription_id.write({'recurring_invoice_line_ids': to_remove, 'description': order.note, 'pricelist_id': order.pricelist_id.id})
                        line.subscription_id.set_open()
                        line.subscription_id.increment_period()
                    if not order.subscription_management:
                        order.subscription_management = 'upsell'
                    # add new lines or increment quantities on existing lines
                    line._update_subscription_line_data(values)
                    msg_body = msg_template.render(values={'line': line})
                    line.subscription_id.message_post(body=msg_body, author_id=self.env.user.partner_id.id)
                else:
                    #make dictionary to get lines of all common template than create subscription based on that.
                    if line.product_id.recurring_invoice:
                        if line.product_id.subscription_template_id.id not in templates.keys():
                            templates[line.product_id.subscription_template_id.id] = {'order': order.id, 'template': line.product_id.subscription_template_id, 'lines': [line]}

                        else:
                            templates[line.product_id.subscription_template_id.id]['lines'].append(line)

            for template_id, subscription_dict in templates.items():
                template = subscription_dict['template']
                lines = subscription_dict['lines']
                subscr_data = line._prepare_subscription_data(template=template)
                subscription = order.env['sale.subscription'].create(subscr_data)
                for line in lines:
                    subscr_line = line._prepare_subscription_line_data(subscription=subscription)
                    subscription.write({'recurring_invoice_line_ids': subscr_line})
                    line.subscription_id = subscription.id
                order.write({
                    'project_id': subscription.analytic_account_id.id,
                    'subscription_management': 'create',
                })
            if any(order.order_line.filtered(lambda line: line.subscription_id)):
                order.action_done()
        return True

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        self.create_subscription()
        return res

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.project_id and self.subscription_management == 'renew':
            subscr = self.env['sale.subscription'].search([('analytic_account_id', '=', self.project_id.id)], limit=1)
            next_date = fields.Date.from_string(subscr.recurring_next_date)
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            previous_date = next_date - relativedelta(**{periods[subscr.recurring_rule_type]: subscr.recurring_interval})

            # DO NOT FORWARDPORT
            format_date = self.env['ir.qweb.field.date'].value_to_html
            invoice_vals['comment'] = _("This invoice covers the following period: %s - %s") % (format_date(fields.Date.to_string(previous_date), {}), format_date(fields.Date.to_string(next_date - relativedelta(days=1)), {}))

        return invoice_vals


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    subscription_id = fields.Many2one('sale.subscription', 'Subscription', copy=False)

    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        if self.subscription_id:
            res['subscription_id'] = self.subscription_id.id
            if self.subscription_id.analytic_account_id:
                res['account_analytic_id'] = self.subscription_id.analytic_account_id.id
        return res

    def _prepare_subscription_data(self, template):
        self.ensure_one()
        order = self.order_id
        values = {
            'name': template.name,
            'state': 'open',
            'template_id': template.id,
            'partner_id': order.partner_id.id,
            'user_id': order.user_id.id,
            'date_start': fields.Date.today(),
            'description': order.note,
            'pricelist_id': order.pricelist_id.id,
            'recurring_rule_type': template.recurring_rule_type,
            'recurring_interval': template.recurring_interval,
            'company_id': order.company_id.id,
        }
        # compute the next date
        today = datetime.date.today()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        invoicing_period = relativedelta(**{periods[values['recurring_rule_type']]: values['recurring_interval']})
        recurring_next_date = today + invoicing_period
        values['recurring_next_date'] = fields.Date.to_string(recurring_next_date)
        if 'template_asset_category_id' in template._fields:
            values['asset_category_id'] = template.with_context(force_company=self.company_id.id).template_asset_category_id.id
        return values

    def _prepare_subscription_line_data(self, subscription):
        self.ensure_one()
        values = [(0, 0, {
            'product_id': self.product_id.id,
            'analytic_account_id': subscription.id,
            'name': self.name,
            'quantity': self.product_uom_qty,
            'uom_id': self.product_uom.id,
            'price_unit': self.price_unit,
            'discount': self.discount if self.order_id.subscription_management != 'upsell' else False,
        })]
        return values

    def _update_subscription_line_data(self, values):
        self.ensure_one()
        sub_lines = self.subscription_id.recurring_invoice_line_ids.filtered(lambda subscr_line: subscr_line.product_id == self.product_id and subscr_line.uom_id == self.product_uom)
        if sub_lines:
            values['recurring_invoice_line_ids'].append((1, sub_lines.id, {
                'quantity': sub_lines.quantity + self.product_uom_qty,
            }))
        else:
            values['recurring_invoice_line_ids'].append(self._prepare_subscription_line_data(self.subscription_id)[0])
        return self.subscription_id.write(values)
