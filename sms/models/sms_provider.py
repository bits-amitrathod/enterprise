# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class SmsProvider(models.Model):

    _name = 'sms.provider'
    _description = "SMS Provider"

    name = fields.Char("Name", required=True)
    provider = fields.Selection([], string='Provider', required=True, help="Provider that will be used to send the SMS text message. Install Providers through modules.")

    def get_default_sms_provider(self):
        provider_id = self.env['ir.config_parameter'].sudo().get_param('default_sms_provider_id', default=False)
        if provider_id:
            return self.env['sms.provider'].browse(provider_id)

    def _send_sms(self, message, mobile_numbers):
        """ Private implementation of SMS sending using the provider gateway.

            Each provider should implement a method named _<provider_name>_send_sms
            where <provider_name> corresponds to the value of the provider field.
            The method should return True if everything went as expected.

            :param message : plaintext message to send by SMS
            :param mobile_numbers : list of mobile numbers
            :return boolean :
                - True : Success
                - False : Failure
        """
        self.ensure_one()
        method = '_%s_send_sms' % (self.provider,)
        if hasattr(self, method):
            return getattr(self, method)(message, mobile_numbers)
        return False

    def _test_sms(self):
        """ Test the SMS Gateway with the current provider : it simply sends an SMS to the current user """
        self.ensure_one()
        if not self.env.user.partner_id.mobile:
            raise UserError(_('Please set your own mobile number in order to test the Odoo SMS Gateway.'))
        return self._send_sms(_('Odoo SMS Gateway Working!'), [self.env.user.partner_id.mobile])
