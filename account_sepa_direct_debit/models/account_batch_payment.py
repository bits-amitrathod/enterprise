# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from datetime import date, datetime

from odoo import models, fields, api, _

from odoo.exceptions import ValidationError, UserError

class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    sdd_xml_file_generation_date = fields.Date(string='SDD File Creation', readonly=True, help="Creation Date of the related SDD XML file.")
    sdd_xml_file = fields.Binary(string='SDD XML File', readonly=True, help="SDD XML file related to this batch")
    sdd_xml_filename = fields.Char(string='SDD XML File Name', help="Name of the SDD XML file generated for this batch", store=True)
    sdd_required_collection_date = fields.Date(string='Required collection date', default=fields.Date.today, readonly=True, states={'draft': [('readonly', '=', False)]}, help="Date when the company expects to receive the payments of this batch.")

    def generate_sdd_xml(self):
        company = self.env['res.company']._company_default_get('account.payment')

        if not company.sdd_creditor_identifier:
            raise UserError(_("Your company must have a creditor identifier in order to issue SEPA Direct Debit payments requests. It can be defined in accounting module's settings."))

        collection_date = datetime.strptime(self.sdd_required_collection_date,'%Y-%m-%d').date()
        if collection_date < date.today():
            raise UserError(_("You cannot generate a SEPA Direct Debit file with a required collection date in the past."))

        # Constrains on models ensure all the payments can generate SDD data before
        # calling this method, so we make no further check of their content here

        self.write({
                'sdd_xml_filename': 'PAIN008' + datetime.now().strftime('%Y%m%d%H%M%S') + '.xml',
                'sdd_xml_file': base64.encodestring(self.payment_ids.generate_xml(company, self.sdd_required_collection_date)),
                'sdd_xml_file_generation_date': fields.Date.today,
        })

        xml_wizard = self.env['sdd.download.xml.wizard'].create({
                'batch_payment_id': self.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sdd.download.xml.wizard',
            'target': 'new',
            'res_id': xml_wizard.id,
        }

    def validate_batch(self):
        res = super(AccountBatchPayment, self).validate_batch()
        if self[0].payment_method_code == 'sdd':
            return self.generate_sdd_xml()
        return res
