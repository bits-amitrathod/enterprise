# -*- coding: utf-8 -*-

from odoo import models, fields


class sale_order_line(models.Model):
    _name = "sale.order.line"
    _inherit = "sale.order.line"

    recurring_product = fields.Boolean('Recurring Product', compute="_compute_recurring")

    def _compute_recurring(self):
        for line in self:
            line.recurring_product = line.sudo().product_id.recurring_invoice
