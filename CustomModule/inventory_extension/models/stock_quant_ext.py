from odoo import models, fields, api
import logging
import datetime


_logger = logging.getLogger(__name__)



class StockQuantExt(models.Model):

    _inherit = 'stock.quant'
    use_date = fields.Char('Expired Date', compute='_compute_show_lot_user_date')

    @api.multi
    def _compute_show_lot_user_date(self):
        _logger.info("(stock_quant_ext) _compute_show_lot_user_date called...")
        _logger.info("%r", self)
        for record in self:
            _logger.info(record.lot_id)
            if record.lot_id and record.lot_id.use_date:
                final_date = datetime.datetime.strptime(record.lot_id.use_date, '%Y-%m-%d %H:%M:%S')
                record.use_date = final_date.date()
