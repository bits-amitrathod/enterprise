from odoo import models, fields, api, exceptions


class SignTemplate(models.Model):
    _inherit = ['sign.template']

    folder_id = fields.Many2one('documents.folder')
    documents_tag_ids = fields.Many2many('documents.tag', string="attachment tags", related="attachment_id.tag_ids")
