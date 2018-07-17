# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import datetime
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

class ScrapSchedular(models.Model):
    _inherit = 'stock.scrap'
    _name = 'stock.scrap'
   
    @api.model
    @api.multi
    def process_scrap_scheduler(self):
        today_date = datetime.datetime.now()
        today_start = fields.Datetime.to_string(today_date)
        location_id = self.env['stock.location'].search([('complete_name', '=', 'Physical Locations/WH/Stock')]).id
        self._cr.execute(""" SELECT
                    sp.id as lot_id,
                    sp.name as name,
                    sp.product_id as product_id,
                    sp.product_uom_id as product_uom_id,
                    sq.quantity as quantity
                    FROM stock_production_lot as sp LEFT JOIN stock_quant as sq 
                    ON sq.lot_id = sp.id where sp.removal_date <= %s AND 
                    sq.location_id=%s AND sq.quantity > 0""",[today_start, location_id])
        product_objects = self._cr.dictfetchall()
        if product_objects:
            for product in product_objects:
                val = {'location_id': location_id, 'date_expected': today_start, 'scrap_qty': product["quantity"],
                    'state': 'draft', 'product_id': product["product_id"], 'scrap_location_id': 4, 'owner_id': False,
                    'product_uom_id': product["product_uom_id"], 'package_id': False, 'picking_id': False, 'origin': False,
                    'lot_id': product["lot_id"]}
                self=self.create(val)
                self.action_validate()
                
    



