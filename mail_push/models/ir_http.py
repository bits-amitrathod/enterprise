# -*- coding: utf-8 -*-

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(IrHttp, self).session_info()
        result.update(
            device_subscription_ids=request.env.user.partner_id.sudo().device_identity_ids.mapped('subscription_id'),
            fcm_project_id=request.env['mail.message']._get_default_fcm_credentials()["fcm_project_id"],
            inbox_action=request.env.ref('mail.action_discuss').id,
        )
        return result
