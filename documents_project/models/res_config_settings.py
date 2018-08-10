# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _get_default_project_folder(self):
        folder_id = self.env.user.company_id.project_folder
        if folder_id.exists():
            return folder_id
        try:
            return self.env.ref('documents_project.documents_project_folder')
        except Exception:
            return False

    project_folder = fields.Many2one('documents.folder', related='company_id.project_folder',
                                     default=_get_default_project_folder,
                                     string="project folder")


