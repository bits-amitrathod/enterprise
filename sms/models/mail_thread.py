# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, _

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _get_default_sms_recipients(self):
        """ This method will likely need to be overriden by inherited models.
               :returns partners: recordset of res.partner
        """
        partners = self.env['res.partner']
        if hasattr(self, 'partner_id'):
            partners |= self.mapped('partner_id')
        if hasattr(self, 'partner_ids'):
            partners |= self.mapped('partner_ids')
        return partners

    def message_post_send_sms(self, sms_message, partners=None, provider=None, note_msg=None):
        """ Send an SMS text message and post an internal note in the chatter if successfull
            :param sms_message: plaintext message to send by sms
            :param partners: the recipients partners, if none are given it will take those
                                from _get_default_sms_recipients
            :param provider: the sms.provider to use to send the SMS,
                                if none is given the default one will be taken.
            :param note_msg: message to log in the chatter, if none is given a default one
                             containing the sms_message is logged
        """
        if not provider:
            provider = self.env['sms.provider'].get_default_sms_provider()
            if not provider:
                _logger.warning(_('Could not send SMS text message as no provider is set.'))
                return False
        if not partners:
            partners = self._get_default_sms_recipients()

        mobile_numbers = filter(None, partners.mapped('mobile'))
        if mobile_numbers:
            if provider._send_sms(sms_message, mobile_numbers):
                mail_message_body = note_msg or _('SMS text message sent: %s') % sms_message
                for record in self:
                    record.message_post(body=mail_message_body)
                return True
        return False
