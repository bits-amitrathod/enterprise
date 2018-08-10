# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re

from datetime import date, datetime

from odoo import models, fields, api, _

from odoo.exceptions import ValidationError, UserError

class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    sdd_required_collection_date = fields.Date(string='Required collection date', default=fields.Date.today, readonly=True, states={'draft': [('readonly', '=', False)]}, help="Date when the company expects to receive the payments of this batch.")

    def _get_methods_generating_files(self):
        rslt = super(AccountBatchPayment, self)._get_methods_generating_files()
        rslt.append('sdd')
        return rslt

    def validate_batch(self):
        if self.payment_method_code == 'sdd':
            company = self.env['res.company']._company_default_get()

            if not company.sdd_creditor_identifier:
                raise UserError(_("Your company must have a creditor identifier in order to issue SEPA Direct Debit payments requests. It can be defined in accounting module's settings."))

            collection_date = self.sdd_required_collection_date
            if collection_date < date.today():
                raise UserError(_("You cannot generate a SEPA Direct Debit file with a required collection date in the past."))

            wrong_comm_payments = self.env['account.payment']
            for payment in self.payment_ids:
                if payment.communication and payment.communication != wrong_comm_payments._sanitize_communication(payment.communication):
                    wrong_comm_payments += payment

            wrong_comm_error_format = _("""The following payments' communications are not SEPA compliant: %s.
                                         To be SEPA compliant, a communication must be made of only latin characters, be maximum 140 characters long, and cannot contain '//' sequence, nor start or end with a / character.""")

            if wrong_comm_payments:
                raise UserError(wrong_comm_error_format % ', '.join(wrong_comm_payments.mapped('name')))


        return super(AccountBatchPayment, self).validate_batch()

    def _generate_export_file(self):
        if self.payment_method_code == 'sdd':
            # Constrains on models ensure all the payments can generate SDD data before
            # calling this method, so we make no further check of their content here

            company = self.env['res.company']._company_default_get()

            return {
                'filename': 'PAIN008' + datetime.now().strftime('%Y%m%d%H%M%S') + '.xml',
                'file': base64.encodestring(self.payment_ids.generate_xml(company, self.sdd_required_collection_date)),
            }

        return super(AccountBatchPayment, self)._generate_export_file()
