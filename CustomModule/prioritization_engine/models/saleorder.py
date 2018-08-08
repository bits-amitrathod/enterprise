from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"
    cust_po = fields.Char("Customer PO", readonly=False)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('engine', 'Prioritization'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('void', 'Voided'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    show_validate = fields.Boolean(
        compute='_compute_show_validate',
        help='Technical field used to compute whether the validate should be shown.')

    @api.multi
    def action_void(self):
        return self.write({'state': 'void'})

    @api.multi
    def unlink(self):
        for order in self:
            if order.state not in ('draft', 'cancel','void'):
               raise UserError(
                    'You can not delete a sent quotation or a sales order! Try to cancel or void it before.')
        return models.Model.unlink(self)

    def action_validate(self):
        self = self.env['stock.picking'].search([('sale_id', '=', self.id)])
        if self.id:
            return self.button_validate()

    def action_assign(self):
        self = self.env['stock.picking'].search([('sale_id', '=', self.id)])
        if self.id:
            return self.action_assign()

    def _compute_show_validate(self):
        self = self.env['stock.picking'].search([('sale_id', '=', self.id)])
        if self.id:
            self._compute_show_validate()

    class SaleOrderLine(models.Model):
        _inherit = "sale.order.line"

        def action_show_details(self):
           self= self.env['stock.move'].search([('sale_line_id', '=', self.id)])
           if self.id:
               return self.action_show_details()