# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DocumentFolder(models.Model):
    _name = 'documents.folder'
    _parent_name = 'parent_folder_id'
    _order = 'sequence'

    @api.model
    def default_get(self, fields):
        res = super(DocumentFolder, self).default_get(fields)
        if self._context.get('folder_id'):
            res['parent_folder_id'] = self._context.get('folder_id')

        return res

    company_id = fields.Many2one('res.company', 'Company')
    parent_folder_id = fields.Many2one('documents.folder', string="Parent folder", ondelete="cascade")
    name = fields.Char()
    children_folder_ids = fields.One2many('documents.folder', 'parent_folder_id', string="Sub folders")
    attachment_ids = fields.One2many('ir.attachment', 'folder_id', string="Documents")
    sequence = fields.Integer('Sequence', default=10)
    share_link_ids = fields.One2many('documents.share', 'folder_id', string="Share links")
    facet_ids = fields.One2many('documents.facet', 'folder_id', string="Tag categories")
    group_ids = fields.Many2many('res.groups', string="Access groups")
