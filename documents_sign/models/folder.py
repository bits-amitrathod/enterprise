# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DocumentFolder(models.Model):
    _inherit = 'documents.folder'

    sign_template_id = fields.One2many('sign.template', 'folder_id')
