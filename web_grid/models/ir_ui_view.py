# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.web_grid.models.models import _GRID_TUP


class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=_GRID_TUP)
