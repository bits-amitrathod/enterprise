# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SendSMS(models.TransientModel):
    _name = 'sms.message.send'

    def default_provider_id(self):
        return self.env['sms.provider'].get_default_sms_provider()

    provider_id = fields.Many2one('sms.provider', 'Provider', default=default_provider_id, required=True)
    message = fields.Text('Message')

    def action_send_sms(self):
        active_model = self._context.get('active_model')
        if self._context.get('active_domain'):
            records = self.env[active_model].search(self._context.get('active_domain'))
        else:
            records = self.env[active_model].browse(self._context.get('active_ids', []))
        records.message_post_send_sms(self.message, provider=self.provider_id)
        return {'type': 'ir.actions.act_window_close'}
