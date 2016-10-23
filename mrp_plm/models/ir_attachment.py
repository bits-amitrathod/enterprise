# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    origin_id = fields.Many2one('ir.attachment', 'Original Attachment', help="Field used in the PLM to handle attachments")
    active = fields.Boolean('Active', default=True)

    @api.multi
    def action_active(self):
        self.active = True

    @api.multi
    def action_unactive(self):
        self.active = False


