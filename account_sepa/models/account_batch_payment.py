# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _

from odoo.exceptions import UserError

import base64

class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    sct_xml_file = fields.Binary('SEPA XML File', readonly=True)
    sct_xml_filename = fields.Char(string='Filename', size=256, readonly=True)

    def generate_sct_xml(self):
        """ Generates the SCT XML related corresponding to this batch and opens a
        wizard allowing downloading it.
        """
        if self.journal_id.bank_account_id.acc_type != 'iban':
            raise UserError(_("The account %s, of journal '%s', is not of type IBAN.\nA valid IBAN account is required to use SEPA features.") % (self.journal_id.bank_account_id.acc_number, self.journal_id.name))

        payments = self.payment_ids.sorted(key=lambda r: r.id)
        for payment in payments:
            if not payment.partner_bank_account_id:
                raise UserError(_("There is no recipient bank account selected for payment '%s'") % payment.name)

        is_generic, warning_msg = self._require_generic_message(self.journal_id, payments)
        wizard = self.env['account.sepa.credit.transfer'].create({
            'batch_payment_id': self.id,
            'is_generic': is_generic,
        })

        if self.journal_id.company_id.sepa_pain_version == 'pain.001.001.03.ch.02':
            xml_doc = wizard._create_pain_001_001_03_ch_document(payments)
        elif self.journal_id.company_id.sepa_pain_version == 'pain.001.003.03':
            xml_doc = wizard._create_pain_001_003_03_document(payments)
        else:
            xml_doc = wizard._create_pain_001_001_03_document(payments)

        self.write({'sct_xml_file': base64.encodestring(xml_doc), 'sct_xml_filename': "SCT-" + self.journal_id.code + "-" + fields.Datetime.now() + ".xml"})

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.sepa.credit.transfer',
            'target': 'new',
            'res_id': wizard.id,
            'context': {'warning_message': warning_msg}
        }

    def _require_generic_message(self, journal, payments):
        """ Find out if generating a credit transfer initiation message for payments requires to use the generic rules, as opposed to the standard ones.
            The generic rules are used for payments which are not considered to be standard european credit transfers.
        """
        # A message is generic if :
        debtor_currency = journal.currency_id and journal.currency_id.name or journal.company_id.currency_id.name
        if debtor_currency != 'EUR':
            return True, _('Your bank account is not labelled in EUR')
        for payment in payments:
            bank_account = payment.partner_bank_account_id
            if payment.currency_id.name != 'EUR':
                return True, _('The transaction %s is instructed in another currency than EUR') % payment.name
            if not bank_account.bank_bic:
                return True, _('The creditor bank account %s used in payment %s is not identified by a BIC') % (payment.partner_bank_account_id.acc_number, payment.name)
            if not bank_account.acc_type == 'iban':
                return True, _('The creditor bank account %s used in payment %s is not identified by an IBAN') % (payment.partner_bank_account_id.acc_number, payment.name)
        return False, ''

    def validate_batch(self):
        res = super(AccountBatchPayment, self).validate_batch()
        if self[0].payment_method_code == 'sepa_ct':
            return self.generate_sct_xml()
        return res
