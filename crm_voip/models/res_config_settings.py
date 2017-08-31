# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    wsServer = fields.Char("WebSocket", help="The URL of your WebSocket")
    pbx_ip = fields.Char("PBX Server IP", help="The IP adress of your PBX Server")
    mode = fields.Selection([
        ('demo', 'Demo'),
        ('prod', 'Production'),
    ], string="Mode")

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('crm.voip.pbx_ip', self[0].pbx_ip)
        params.set_param('crm.voip.wsServer', self[0].wsServer)
        params.set_param('crm.voip.mode', self[0].mode)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            pbx_ip=params.get_param('crm.voip.pbx_ip', default='localhost'),
            wsServer=params.get_param('crm.voip.wsServer', default='ws://localhost'),
            mode=params.get_param('crm.voip.mode', default="demo"),
        )
        return res
