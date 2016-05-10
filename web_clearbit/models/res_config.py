# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    module_web_clearbit = fields.Boolean(string='Get Company Information From Clearbit',
        help="""This installs the module web_clearbit.""")
