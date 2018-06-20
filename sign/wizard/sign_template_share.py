# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import api, fields, models, _


class SignTemplateShare(models.TransientModel):
    _name = 'sign.template.share'

    @api.model
    def default_get(self, fields):
        res = super(SignTemplateShare, self).default_get(fields)
        res['template_id'] = self.env.context.get('active_id')
        template = self.env['sign.template'].browse(res['template_id'])
        if len(template.sign_item_ids.mapped('responsible_id')) > 1:
            res['url'] = False
        else:
            if not template.share_link:
                template.share_link = str(uuid.uuid4())
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            res['url'] = "%s/sign/%s" % (base_url, template.share_link)
        return res

    template_id = fields.Many2one('sign.template', required=True)
    url = fields.Char(string="Link to Share")
    is_one_responsible = fields.Boolean()
