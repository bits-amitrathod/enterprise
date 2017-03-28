# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _name = "sale.order"

    subscription_template = fields.Many2one('sale.subscription.template', 'Subscription Template',
        help="If set, all recurring products in this Sales Order will be included in a new Subscription with the selected template")

    @api.onchange('template_id')
    def onchange_template_id(self):
        super(SaleOrder, self).onchange_template_id()
        if self.template_id.subscription_template:
            self.subscription_template = self.template_id.subscription_template.id

    @api.onchange('subscription_template')
    def onchange_subscription_template(self):
        if not self.template_id.subscription_template:
            subscription_lines = [(0, 0, {
                'product_id': mand_line.product_id.id,
                'uom_id': mand_line.uom_id.id,
                'name': mand_line.name,
                'product_uom_qty': mand_line.quantity,
                'product_uom': mand_line.uom_id.id,
                'price_unit': self.pricelist_id.get_product_price(mand_line.product_id, 1, self.partner_id, uom_id=mand_line.uom_id.id) if self.pricelist_id else 0,
            }) for mand_line in self.subscription_template.subscription_template_line_ids]
            options = [(0, 0, {
                'product_id': opt_line.product_id.id,
                'uom_id': opt_line.uom_id.id,
                'name': opt_line.name,
                'quantity': opt_line.quantity,
                'price_unit': self.pricelist_id.get_product_price(opt_line.product_id, 1, self.partner_id, uom_id=opt_line.uom_id.id) if self.pricelist_id else 0,
            }) for opt_line in self.subscription_template.subscription_template_option_ids]
            self.order_line = subscription_lines
            for line in self.order_line:
                line._compute_tax_id()
            self.options = options
            if self.subscription_template:
                self.note = self.subscription_template.description

    def create_subscription(self):
        """ Create a subscription based on the order's quote template's subscription template """
        self.ensure_one()
        if self.require_payment:
            payment_token = self.payment_tx_id.payment_token_id
        if (self.template_id and self.template_id.subscription_template or self.subscription_template) and not self.subscription_id \
                and any(self.order_line.mapped('product_id').mapped('recurring_invoice')):
            values = self._prepare_subscription_data(payment_token_id=payment_token.id if self.require_payment else False)
            subscription = self.env['sale.subscription'].sudo().create(values)
            subscription.name = self.partner_id.name + ' - ' + subscription.code

            invoice_line_ids = []
            for line in self.order_line:
                if line.product_id.recurring_invoice:
                    contract_line = line._prepare_contract_line(subscription)
                    invoice_line_ids.append((0, 0, contract_line))
            if invoice_line_ids:
                sub_values = {'recurring_invoice_line_ids': invoice_line_ids}
                subscription.write(sub_values)

            self.write({
                'project_id': subscription.analytic_account_id.id,
                'subscription_management': 'create',
            })
            return subscription
        return False

    def _prepare_subscription_data(self, payment_token_id=False):
        if self.template_id and self.template_id.subscription_template:
            subscription_tmp = self.template_id.subscription_template
        else:
            subscription_tmp = self.subscription_template
        values = {
            'name': subscription_tmp.name,
            'state': 'open',
            'template_id': subscription_tmp.id,
            'partner_id': self.partner_id.id,
            'user_id': self.user_id.id,
            'date_start': fields.Date.today(),
            'description': self.note,
            'payment_token_id': payment_token_id,
            'pricelist_id': self.pricelist_id.id,
            'recurring_rule_type': subscription_tmp.recurring_rule_type,
            'recurring_interval': subscription_tmp.recurring_interval,
            'company_id': self.company_id.id,
        }
        # if there already is an AA, use it in the subscription's inherits
        if self.project_id:
            values.pop('name')
            values.pop('partner_id')
            values.pop('company_id')
            values['analytic_account_id'] = self.project_id.id
        # compute the next date
        today = datetime.date.today()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        invoicing_period = relativedelta(**{periods[values['recurring_rule_type']]: values['recurring_interval']})
        recurring_next_date = today + invoicing_period
        values['recurring_next_date'] = fields.Date.to_string(recurring_next_date)
        if 'template_asset_category_id' in subscription_tmp._fields:
            values['asset_category_id'] = subscription_tmp.with_context(force_company=self.company_id.id).template_asset_category_id.id
        return values

    @api.multi
    def action_confirm(self):
        no_upsell = dict.fromkeys(self.ids)  # avoid adding options again in sale_subscription override
        msg_template = self.env.ref('website_subscription.chatter_add_paid_option')
        for order in self:
            if order.subscription_id and any(order.order_line.mapped('product_id').mapped('recurring_invoice')):
                lines = order.order_line.filtered(lambda s: s.product_id.recurring_invoice)
                msg_body = msg_template.render(values={'lines': lines})
                # done as sudo since salesman may not have write rights on subscriptions
                order.subscription_id.sudo().message_post(body=msg_body, author_id=self.env.user.partner_id.id)
            no_upsell[order.id] = order.create_subscription()
        return super(SaleOrder, self.with_context(no_upsell=no_upsell)).action_confirm()

    # DBO: the following is there to amend the behaviour of website_sale:
    # - do not update price on sale_order_line where force_price = True
    #   (some options may have prices that are different from the product price)
    # - prevent having a cart with options for different subscriptions (project_id)
    # If we ever decide to move the payment code out of website_sale, we should scrap all this
    def set_project_id(self, account_id):
        """ Set the specified account_id sale.subscription as the sale_order project_id
        and remove all the recurring products from the sales order if the field was already defined"""
        account = self.env['sale.subscription'].browse(account_id)
        if self.project_id != account:
            self.reset_project_id()
        self.write({'project_id': account.analytic_account_id.id, 'user_id': account.user_id.id, 'subscription_management': 'upsell'})

    def reset_project_id(self):
        """ Remove the project_id of the sales order and remove all sale.order.line whose
        product is recurring"""
        data = []
        for line in self.order_line:
            if line.product_id.product_tmpl_id.recurring_invoice:
                data.append((2, line.id))
        self.write({'order_line': data, 'project_id': False})

    def _get_payment_type(self):
        if any(line.product_id.recurring_invoice for line in self.sudo().order_line):
            return 'form_save'
        return super(SaleOrder, self)._get_payment_type()

    def _website_product_id_change(self, order_id, product_id, qty=0):
        res = super(SaleOrder, self)._website_product_id_change(order_id, product_id, qty)
        line = self._cart_find_product_line(product_id=product_id)
        if line and line.force_price:
            res['price_unit'] = line.price_unit
            res['product_uom'] = line.product_uom.id
        return res


class sale_order_line(models.Model):
    _inherit = "sale.order.line"
    _name = "sale.order.line"

    force_price = fields.Boolean('Force price', help='Force a specific price, regardless of any coupons or pricelist change', default=False)

    def _prepare_contract_line(self, subscription):
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'analytic_account_id': subscription.id,
            'name': self.name,
            'quantity': self.product_uom_qty,
            'discount': self.discount,
            'uom_id': self.product_uom.id,
            'price_unit': self.price_unit,
        }
