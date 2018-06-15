# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountBatchPayment(models.Model):
    _name = "account.batch.payment"
    _description = "Batch Payment"
    _order = "date desc, id desc"

    name = fields.Char(required=True, copy=False, string='Reference', readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date(required=True, copy=False, default=fields.Date.context_today, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'New'), ('sent', 'Sent'), ('reconciled', 'Reconciled')], readonly=True, default='draft', copy=False)
    journal_id = fields.Many2one('account.journal', string='Bank', domain=[('type', '=', 'bank')], required=True, readonly=True, states={'draft': [('readonly', False)]})
    payment_ids = fields.One2many('account.payment', 'batch_payment_id', string="Payments", required=True, readonly=True, states={'draft': [('readonly', False)]})
    amount = fields.Monetary(compute='_compute_amount', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', store=True, readonly=True)
    batch_type = fields.Selection(selection=[('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True, readonly=True, states={'draft': [('readonly', '=', False)]}, default='inbound')
    payment_method_id = fields.Many2one(comodel_name='account.payment.method', string='Payment Method', required=True, readonly=True, states={'draft': [('readonly', '=', False)]}, help="The payment method used by the payments in this batch.")
    payment_method_code = fields.Char(related='payment_method_id.code')

    available_payment_method_ids = fields.One2many(comodel_name='account.payment', compute='_compute_available_payment_method_ids')

    @api.depends('journal_id', 'batch_type')
    def _compute_available_payment_method_ids(self):
        for record in self:
            record.available_payment_method_ids = record.batch_type == 'inbound' and record.journal_id.inbound_payment_method_ids.ids or record.journal_id.outbound_payment_method_ids.ids

    @api.one
    @api.depends('journal_id')
    def _compute_currency(self):
        if self.journal_id:
            self.currency_id = self.journal_id.currency_id or self.journal_id.company_id.currency_id
        else:
            self.currency_id = False

    @api.one
    @api.depends('payment_ids', 'payment_ids.amount', 'journal_id')
    def _compute_amount(self):
        company_currency = self.journal_id.company_id.currency_id or self.env.user.company_id.currency_id
        journal_currency = self.journal_id.currency_id or company_currency
        amount = 0
        for payment in self.payment_ids:
            payment_currency = payment.currency_id or company_currency
            if payment_currency == journal_currency:
                amount += payment.amount
            else:
                # Note : this makes self.date the value date, which IRL probably is the date of the reception by the bank
                amount += payment_currency._convert(payment.amount, journal_currency, self.journal_id.company_id, self.date or fields.Date.today())
        self.amount = amount

    @api.constrains('batch_type', 'journal_id', 'payment_ids')
    def _check_payments_constrains(self):
        for record in self:
            all_companies = set(record.payment_ids.mapped('company_id'))
            if len(all_companies) > 1:
                raise ValidationError(_("All payments in the batch must belong to the same company."))
            all_journals = set(record.payment_ids.mapped('journal_id'))
            if len(all_journals) > 1 or record.payment_ids[0].journal_id != record.journal_id:
                raise ValidationError(_("The journal of the batch payment and of the payments it contains must be the same."))
            all_types = set(record.payment_ids.mapped('payment_type'))
            if len(all_types) > 1:
                raise ValidationError(_("All payments in the batch must share the same type."))
            if all_types and record.batch_type not in all_types:
                raise ValidationError(_("The batch must have the same type as the payments it contains."))
            all_payment_methods = set(record.payment_ids.mapped('payment_method_id'))
            if len(all_payment_methods) > 1:
                raise ValidationError(_("All payments in the batch must share the same payment method."))
            if all_payment_methods and record.payment_method_id not in all_payment_methods:
                raise ValidationError(_("The batch must have the same payment method as the payments it contains."))

    @api.model
    def create(self, vals):
        vals['name'] = self._get_batch_name(vals.get('batch_type'), vals.get('date', fields.Date.context_today(self)), vals)
        rec = super(AccountBatchPayment, self).create(vals)
        rec.normalize_payments()
        return rec

    @api.multi
    def write(self, vals):
        if 'batch_type' in vals:
            vals['name'] = self.with_context(default_journal_id = self.journal_id.id)._get_batch_name(vals['batch_type'], self.date, vals)

        rslt = super(AccountBatchPayment, self).write(vals)

        if 'payment_ids' in vals:
            self.normalize_payments()

        return rslt

    @api.one
    def normalize_payments(self):
        # Since a batch payment has no confirmation step (it can be used to select payments in a bank reconciliation
        # as long as state != reconciled), its payments need to be posted
        self.payment_ids.filtered(lambda r: r.state == 'draft').post()

    @api.model
    def _get_batch_name(self, batch_type, sequence_date, vals):
        if not vals.get('name'):
            sequence_code = 'account.inbound.batch.payment'
            if batch_type == 'outbound':
                sequence_code = 'account.outbound.batch.payment'
            return self.env['ir.sequence'].with_context(sequence_date=sequence_date).next_by_code(sequence_code)
        return vals['name']

    def validate_batch(self):
        records = self.filtered(lambda x: x.state == 'draft')
        for record in records:
            record.payment_ids.write({'state':'sent', 'payment_reference': record.name})
        records.write({'state': 'sent'})

    @api.multi
    def print_batch_payment(self):
        return self.env.ref('account_batch_payment.action_print_batch_payment').report_action(self, config=False)
