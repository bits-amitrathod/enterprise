# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SignSendRequest(models.TransientModel):
    _name = 'sign.send.request'

    @api.model
    def default_get(self, fields):
        res = super(SignSendRequest, self).default_get(fields)
        res['template_id'] = self.env.context.get('active_id')
        template = self.env['sign.template'].browse(res['template_id'])
        res['filename'] = template.attachment_id.name
        res['subject'] = "Signature Request - %s" % (template.attachment_id.name)
        roles = template.mapped('sign_item_ids.responsible_id')
        res['signers_count'] = len(roles)
        res['signer_ids'] = [(0, 0, {
            'role_id': role.id,
            'partner_id': False,
        }) for role in roles]
        return res

    template_id = fields.Many2one('sign.template', required=True)
    signer_ids = fields.One2many('sign.send.request.signer', 'sign_send_request_id', string="Signers")
    signer_id = fields.Many2one('res.partner', string="Signer")
    signers_count = fields.Integer()
    follower_ids = fields.Many2many('res.partner', string="Send a copy to")
    extension = fields.Char(compute='_compute_extension')

    subject = fields.Char(string="Subject")
    message = fields.Text("Message")
    filename = fields.Char("Filename")

    @api.depends('template_id.attachment_id.datas_fname')
    def _compute_extension(self):
        for wizard in self.filtered(lambda w: w.template_id):
            wizard.extension = '.' + self.template_id.attachment_id.datas_fname.split('.')[-1]

    def send_request(self):
        template_id = self.template_id.id
        if self.signers_count:
            signers = [{'partner_id': signer.partner_id.id, 'role': signer.role_id.id} for signer in self.signer_ids]
        else:
            signers = [{'partner_id': self.signer_id.id, 'role': False}]
        followers = self.follower_ids.ids
        reference = self.filename
        subject = self.subject
        message = self.message
        res = self.env['sign.request'].initialize_new(template_id, signers, followers, reference, subject, message)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Signature(s)',
            'view_mode': 'form',
            'res_model': 'sign.request',
            'res_id': res['id']
        }


class SignSendRequestSigner(models.TransientModel):
    _name = "sign.send.request.signer"

    role_id = fields.Many2one('sign.item.role', readonly=True)
    partner_id = fields.Many2one('res.partner', required=True)
    sign_send_request_id = fields.Many2one('sign.send.request')
