# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta
import logging
import time
import traceback
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv.query import Query

_logger = logging.getLogger(__name__)


class SaleSubscription(models.Model):
    _inherit = "sale.subscription"

    uuid = fields.Char('Account UUID', default=lambda s: uuid.uuid4(), copy=False, required=True)
    website_url = fields.Char('Website URL', compute='_website_url', help='The full URL to access the document through the website.')
    payment_token_id = fields.Many2one('payment.token', 'Payment Token', help='If not set, the default payment token of the partner will be used.', domain="[('partner_id','=',partner_id)]", oldname='payment_method_id')
    # add tax calculation
    recurring_amount_tax = fields.Float('Taxes', compute="_amount_all")
    recurring_amount_total = fields.Float('Total', compute="_amount_all")

    _sql_constraints = [
        ('uuid_uniq', 'unique (uuid)', """UUIDs (Universally Unique IDentifier) for Sale Subscriptions should be unique!"""),
    ]

    @api.model_cr_context
    def _init_column(self, column_name):
        # to avoid generating a single default uuid when installing the module,
        # we need to set the default row by row for this column
        if column_name == "uuid":
            _logger.debug("Table '%s': setting default value of new column %s to unique values for each row",
                          self._table, column_name)
            self.env.cr.execute("SELECT id FROM %s WHERE uuid IS NULL" % self._table)
            acc_ids = self.env.cr.dictfetchall()
            query_list = [{'id': acc_id['id'], 'uuid': str(uuid.uuid4())} for acc_id in acc_ids]
            query = 'UPDATE ' + self._table + ' SET uuid = %(uuid)s WHERE id = %(id)s;'
            self.env.cr._obj.executemany(query, query_list)
            self.env.cr.commit()

        else:
            super(SaleSubscription, self)._init_column(column_name)

    @api.depends('recurring_invoice_line_ids', 'recurring_total')
    def _amount_all(self):
        for account in self:
            account_sudo = account.sudo()
            val = val1 = 0.0
            cur = account_sudo.pricelist_id.currency_id
            for line in account_sudo.recurring_invoice_line_ids:
                val1 += line.price_subtotal
                val += line._amount_line_tax()
            account.recurring_amount_tax = cur.round(val)
            account.recurring_amount_total = account.recurring_amount_tax + account.recurring_total

    @api.depends('uuid')
    def _website_url(self):
        for account in self:
            account.website_url = '/my/subscription/%s/%s' % (account.id, account.uuid)

    @api.multi
    def open_website_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.website_url,
            'target': 'self',
        }

    def add_option(self, option_id):
        pass

    def set_option(self, subscription, new_option, price):
        pass

    def remove_option(self, option_id):
        pass

    def _compute_options(self):
        pass

       # online payments
    @api.one
    def _do_payment(self, payment_token, invoice, two_steps_sec=True):
        tx_obj = self.env['payment.transaction']
        reference = "SUB%s-%s" % (self.id, datetime.datetime.now().strftime('%y%m%d_%H%M%S'))
        values = {
            'amount': invoice.amount_total,
            'acquirer_id': payment_token.acquirer_id.id,
            'type': 'server2server',
            'currency_id': invoice.currency_id.id,
            'reference': reference,
            'payment_token_id': payment_token.id,
            'partner_id': self.partner_id.id,
            'partner_country_id': self.partner_id.country_id.id,
            'invoice_id': invoice.id,
            'callback_model_id': self.env['ir.model'].sudo().search([('model', '=', self._name)], limit=1).id,
            'callback_res_id': self.id,
            'callback_method': 'reconcile_pending_transaction',
        }

        tx = tx_obj.create(values)

        baseurl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        payment_secure = {'3d_secure': two_steps_sec,
                          'accept_url': baseurl + '/my/subscription/%s/payment/%s/accept/' % (self.uuid, tx.id),
                          'decline_url': baseurl + '/my/subscription/%s/payment/%s/decline/' % (self.uuid, tx.id),
                          'exception_url': baseurl + '/my/subscription/%s/payment/%s/exception/' % (self.uuid, tx.id),
                          }
        tx.s2s_do_transaction(**payment_secure)
        return tx

    @api.multi
    def reconcile_pending_transaction(self, tx, invoice=False):
        self.ensure_one()
        if not invoice:
            invoice = tx.invoice_id
        if tx.state in ['done', 'authorized']:
            invoice.write({'reference': tx.reference, 'name': tx.reference})
            if tx.acquirer_id.journal_id and tx.state == 'done':
                invoice.action_invoice_open()
                journal = tx.acquirer_id.journal_id
                invoice.with_context(default_ref=tx.reference, default_currency_id=tx.currency_id.id).pay_and_reconcile(journal, pay_amount=tx.amount)
            self.increment_period()
            self.write({'state': 'open', 'date': False})
        else:
            invoice.action_cancel()
            invoice.unlink()

    @api.multi
    def _recurring_create_invoice(self, automatic=False):
        cr = self.env.cr
        invoice_ids = []
        current_date = time.strftime('%Y-%m-%d')
        imd_res = self.env['ir.model.data']
        template_res = self.env['mail.template']
        if len(self) > 0:
            subscriptions = self
        else:
            domain = [('recurring_next_date', '<=', current_date),
                      ('state', 'in', ['open', 'pending'])]
            subscriptions = self.search(domain)
        if subscriptions:
            cr.execute('SELECT a.company_id, array_agg(sub.id) as ids FROM sale_subscription as sub JOIN account_analytic_account as a ON sub.analytic_account_id = a.id WHERE sub.id IN %s GROUP BY a.company_id', (tuple(subscriptions.ids),))
            for company_id, ids in cr.fetchall():
                context_company = dict(self.env.context, company_id=company_id, force_company=company_id)
                for subscription in self.with_context(context_company).browse(ids):
                    cr.commit()
                    # payment + invoice (only by cron)
                    if subscription.template_id.payment_mandatory and subscription.recurring_total and automatic:
                        try:
                            payment_token = subscription.payment_token_id
                            if payment_token:
                                invoice_values = subscription.with_context(lang=subscription.partner_id.lang)._prepare_invoice()
                                new_invoice = self.env['account.invoice'].with_context(context_company).create(invoice_values)
                                new_invoice.message_post_with_view('mail.message_origin_link',
                                    values = {'self': new_invoice, 'origin': subscription},
                                    subtype_id = self.env.ref('mail.mt_note').id)
                                new_invoice.with_context(context_company).compute_taxes()
                                tx = subscription._do_payment(payment_token, new_invoice, two_steps_sec=False)[0]
                                # commit change as soon as we try the payment so we have a trace somewhere
                                cr.commit()
                                if tx.state in ['done', 'authorized']:
                                    subscription.send_success_mail(tx, new_invoice)
                                    msg_body = 'Automatic payment succeeded. Payment reference: <a href=# data-oe-model=payment.transaction data-oe-id=%d>%s</a>; Amount: %s. Invoice <a href=# data-oe-model=account.invoice data-oe-id=%d>View Invoice</a>.' % (tx.id, tx.reference, tx.amount, new_invoice.id)
                                    subscription.message_post(body=msg_body)
                                    cr.commit()
                                else:
                                    cr.rollback()
                                    new_invoice.unlink()
                                    amount = subscription.recurring_total
                                    date_close = datetime.datetime.strptime(subscription.recurring_next_date, "%Y-%m-%d") + relativedelta(days=15)
                                    close_subscription = current_date >= date_close.strftime('%Y-%m-%d')
                                    email_context = self.env.context.copy()
                                    email_context.update({
                                        'payment_token': subscription.payment_token_id and subscription.payment_token_id.name,
                                        'renewed': False,
                                        'total_amount': amount,
                                        'email_to': subscription.partner_id.email,
                                        'code': subscription.code,
                                        'currency': subscription.pricelist_id.currency_id.name,
                                        'date_end': subscription.date,
                                        'date_close': date_close.date()
                                    })
                                    _logger.error('Fail to create recurring invoice for subscription %s', subscription.code)
                                    if close_subscription:
                                        _, template_id = imd_res.get_object_reference('website_subscription', 'email_payment_close')
                                        template = template_res.browse(template_id)
                                        template.with_context(email_context).send_mail(subscription.id)
                                        _logger.debug("Sending Subscription Closure Mail to %s for subscription %s and closing subscription", subscription.partner_id.email, subscription.id)
                                        msg_body = 'Automatic payment failed after multiple attempts. Subscription closed automatically.'
                                        subscription.message_post(body=msg_body)
                                    else:
                                        _, template_id = imd_res.get_object_reference('website_subscription', 'email_payment_reminder')
                                        msg_body = 'Automatic payment failed. Subscription set to "To Renew".'
                                        if (datetime.datetime.today() - datetime.datetime.strptime(subscription.recurring_next_date, '%Y-%m-%d')).days in [0, 3, 7, 14]:
                                            template = template_res.browse(template_id)
                                            template.with_context(email_context).send_mail(subscription.id)
                                            _logger.debug("Sending Payment Failure Mail to %s for subscription %s and setting subscription to pending", subscription.partner_id.email, subscription.id)
                                            msg_body += ' E-mail sent to customer.'
                                        subscription.message_post(body=msg_body)
                                    subscription.write({'state': 'close' if close_subscription else 'pending'})
                                    cr.commit()
                        except Exception:
                            cr.rollback()
                            # we assume that the payment is run only once a day
                            last_tx = self.env['payment.transaction'].search([('reference', 'like', 'SUBSCRIPTION-%s-%s' % (subscription.id, datetime.date.today().strftime('%y%m%d')))], limit=1)
                            error_message = "Error during renewal of subscription %s (%s)" % (subscription.code, 'Payment recorded: %s' % last_tx.reference if last_tx and last_tx.state == 'done' else 'No payment recorded.')
                            traceback_message = traceback.format_exc()
                            _logger.error(error_message)
                            _logger.error(traceback_message)

                    # invoice only
                    else:
                        try:
                            invoice_values = subscription.with_context(lang=subscription.partner_id.lang)._prepare_invoice()
                            new_invoice = self.env['account.invoice'].with_context(context_company).create(invoice_values)
                            new_invoice.message_post_with_view('mail.message_origin_link',
                                values = {'self': new_invoice, 'origin': subscription},
                                subtype_id = self.env.ref('mail.mt_note').id)
                            new_invoice.with_context(context_company).compute_taxes()
                            invoice_ids.append(new_invoice.id)
                            next_date = datetime.datetime.strptime(subscription.recurring_next_date or current_date, "%Y-%m-%d")
                            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
                            invoicing_period = relativedelta(**{periods[subscription.recurring_rule_type]: subscription.recurring_interval})
                            new_date = next_date + invoicing_period
                            subscription.write({'recurring_next_date': new_date.strftime('%Y-%m-%d')})
                            if automatic:
                                cr.commit()
                        except Exception:
                            if automatic:
                                cr.rollback()
                                _logger.exception('Fail to create recurring invoice for subscription %s', subscription.code)
                            else:
                                raise
        return invoice_ids

    def send_success_mail(self, tx, invoice):
        imd_res = self.env['ir.model.data']
        template_res = self.env['mail.template']
        current_date = time.strftime('%Y-%m-%d')
        next_date = datetime.datetime.strptime(self.recurring_next_date or current_date, "%Y-%m-%d")
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        invoicing_period = relativedelta(**{periods[self.recurring_rule_type]: self.recurring_interval})
        new_date = next_date + invoicing_period
        _, template_id = imd_res.get_object_reference('website_subscription', 'email_payment_success')
        email_context = self.env.context.copy()
        email_context.update({
            'payment_token': self.payment_token_id.name,
            'renewed': True,
            'total_amount': tx.amount,
            'next_date': new_date.date(),
            'previous_date': self.recurring_next_date,
            'email_to': self.partner_id.email,
            'code': self.code,
            'currency': self.pricelist_id.currency_id.name,
            'date_end': self.date,
        })
        _logger.debug("Sending Payment Confirmation Mail to %s for subscription %s", self.partner_id.email, self.id)
        template = template_res.browse(template_id)
        return template.with_context(email_context).send_mail(invoice.id)


class SaleSubscriptionTemplate(models.Model):
    _inherit = "sale.subscription.template"

    user_closable = fields.Boolean(string="Closable by customer", help="If checked, the user will be able to close his account from the frontend")
    payment_mandatory = fields.Boolean('Automatic Payment', help='If set, payments will be made automatically and invoices will not be generated if payment attempts are unsuccessful.')
    tag_ids = fields.Many2many('account.analytic.tag', 'sale_subscription_template_tag_rel', 'template_id', 'tag_id', string='Tags')
    subscription_count = fields.Integer(compute='_compute_subscription_count')
    color = fields.Integer()

    def _compute_subscription_count(self):
        subscription_data = self.env['sale.subscription'].read_group(domain=[('template_id', 'in', self.ids), ('state', 'in', ['open', 'pending'])],
                                                                     fields=['template_id'],
                                                                     groupby=['template_id'])
        mapped_data = dict([(m['template_id'][0], m['template_id_count']) for m in subscription_data])
        for template in self:
            template.subscription_count = mapped_data.get(template.id, 0)


class SaleSubscriptionLine(models.Model):
    _inherit = "sale.subscription.line"

    def get_template_option_line(self):
        """ Return the account.analytic.invoice.line.option which has the same product_id as
        the invoice line"""
        if not self.analytic_account_id and not self.analytic_account_id.template_id:
            return False
        template = self.analytic_account_id.template_id
        return template.sudo().subscription_template_option_ids.filtered(lambda r: r.product_id == self.product_id)

    def _amount_line_tax(self):
        self.ensure_one()
        val = 0.0
        product = self.product_id
        product_tmp = product.sudo().product_tmpl_id
        for tax in product_tmp.taxes_id.filtered(lambda t: t.company_id == self.analytic_account_id.company_id):
            fpos_obj = self.env['account.fiscal.position']
            partner = self.analytic_account_id.partner_id
            fpos_id = fpos_obj.with_context(force_company=self.analytic_account_id.company_id.id).get_fiscal_position(partner.id)
            fpos = fpos_obj.browse(fpos_id)
            if fpos:
                tax = fpos.map_tax(tax, product, partner)
            compute_vals = tax.compute_all(self.price_unit * (1 - (self.discount or 0.0) / 100.0), self.analytic_account_id.currency_id, self.quantity, product, partner)['taxes']
            if compute_vals:
                val += compute_vals[0].get('amount', 0)
        return val
