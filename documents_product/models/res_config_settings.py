# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _get_default_product_folder(self):
        folder_id = self.env.user.company_id.product_folder
        if folder_id.exists():
            return folder_id
        return False

    dms_product_settings = fields.Boolean(related='company_id.dms_product_settings',
                                      default=lambda self: self.env.user.company_id.dms_product_settings)
    product_folder = fields.Many2one('documents.folder', related='company_id.product_folder',
                                 default=_get_default_product_folder,
                                 string="Product Folder")
    product_tags = fields.Many2many('documents.tag', 'product_tags_table', related='company_id.product_tags',
                                default=lambda self: self.env.user.company_id.product_tags.ids,
                                string="Product Tags")
