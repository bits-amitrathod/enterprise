# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _



class StockPackOperation(models.Model):
    _inherit = 'stock.pack.operation'

    lot_barcode = fields.Char(related="lot_id.name")