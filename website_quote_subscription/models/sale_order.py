# -*- coding: utf-8 -*-
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _name = "sale.order"

    def _get_payment_type(self):
        if any(line.product_id.recurring_invoice for line in self.sudo().order_line):
            return 'form_save'
        return super(SaleOrder, self)._get_payment_type()

