# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class MrpProductionWorkcenterLine(models.Model):
    _inherit = 'mrp.workorder'

    def action_print(self):
        if self.product_id.tracking == 'none':
            # go to next step before generate file because of the return
            self._next()
            if self.product_id.uom_id.category_id.measure_type == 'unit':
                qty = int(self.qty_producing)
            else:
                qty = 1
            return self.env.ref(
                'stock_zebra.label_barcode_product_product'
            ).report_action([self.product_id.id] * qty)
        else:
            if self.final_lot_id:
                self._next()
                if self.product_id.uom_id.category_id.measure_type == 'unit':
                    qty = int(self.qty_producing)
                else:
                    qty = 1
                return self.env.ref(
                    'stock_zebra.label_lot_template'
                ).report_action([self.final_lot_id.id] * qty)
            else:
                raise UserError(_('You did not set a lot/serial number for '
                'the final product'))
