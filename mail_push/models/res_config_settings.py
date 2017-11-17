# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mail_push_notification = fields.Boolean('Notifications', oldname="default_mail_push_notification",
                                            config_parameter='mail_push.mail_push_notification')
    fcm_api_key = fields.Char('Server API Key', default='', config_parameter='mail_push.fcm_api_key')
    fcm_project_id = fields.Char('Sender ID', default='', config_parameter='mail_push.fcm_project_id')
