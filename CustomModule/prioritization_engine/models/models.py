# -*- coding: utf-8 -*-
#from addons.sale.models.sale import SaleOrder
from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError


class Customer(models.Model):
    _inherit = 'res.partner'
    prioritization = fields.Boolean("Prioritization setting")
    sku_preconfig=fields.Char("SKU PreConfig")
    sku_postconfig = fields.Char("SKU PostConfig")
    prioritization_ids = fields.One2many('sps.prioritization', 'customer_id')
    sps_sku = fields.Char("SPS SKU", readonly=False)
    threshold = fields.Integer("Product Threshold", readonly=False)
    priority = fields.Integer("Product Priority", readonly=False)
    cooling_period = fields.Integer("Cooling Period in days", readonly=False)
    auto_allocate = fields.Boolean("Allow Auto Allocation?", readonly=False)
    length_of_hold = fields.Integer("Length Of Hold in days", readonly=False)
    expiration_tolerance = fields.Integer("Expiration Tolerance days", readonly=False)
    partial_ordering = fields.Boolean("Allow Partial Ordering?", readonly=False)
    partial_UOM = fields.Integer("Allow Partial UOM?", readonly=False)
    order_ids = fields.One2many('sale.order', 'partner_id')
    gl_account=fields.Char("GL Account")
    on_hold= fields.Boolean("On Hold")


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    tier = fields.Selection([
        ('1', 'I'),
        ('2', 'II')], string='TIER Type')
    location = fields.Char("Location")
    class_code = fields.Char("Class Code")


class Prioritization(models.Model):
    _name = 'prioritization_engine.prioritization'
    _inherits = {'product.product':'product_id'}
    sps_sku = fields.Char("SPS SKU",readonly=False)
    threshold = fields.Integer("Product Threshold",readonly=False)
    priority=fields.Integer("Product Priority",readonly=False)
    cooling_period=fields.Integer("Cooling Period in days",readonly=False)
    auto_allocate=fields.Boolean("Allow Auto Allocation?",readonly=False)
    length_of_hold = fields.Integer("Length Of Hold in days",readonly=False)
    expiration_tolerance = fields.Integer("Expiration Tolerance days",readonly=False)
    partial_ordering = fields.Boolean("Allow Partial Ordering?",readonly=False)
    partial_UOM = fields.Integer("Allow Partial UOM?",readonly=False)
    length_of_hold = fields.Date("Lenght Of Holding",readonly=False)
    customer_id = fields.Many2one('res.partner', string='GlobalPrioritization',required=True)
    product_id = fields.Many2one('product.product', string='Prioritization Product',required=True)
    _sql_constraints = [
        ('sps_company_uniq', 'unique(customer_id,product_id)', 'Product must be unique for customer!!!!'),
       ]

class SaleOrder(models.Model):
    _inherit = "sale.order"
    cust_po = fields.Char("Customer PO", readonly=False)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('void', 'Voided'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

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

    #class SaleOrderLine(models.Model):
        #_inherit = 'sale.order.line'
        #move_line_ids = fields.One2many('stock.move.line', 'move_id')


    #class GolbalPrioritization(models.Model):
        #_name = 'sps.globalprioritization'
        #sps_sku = fields.Char("SPS SKU",readonly=False)
        #threshold = fields.Integer("Product Threshold",readonly=False)
        #priority=fields.Integer("Product Priority",readonly=False)
        #cooling_period=fields.Integer("Cooling Period in days",readonly=False)
        #auto_allocate=fields.Boolean("Allow Auto Allocation?",readonly=False)
        #length_of_hold = fields.Integer("Length Of Hold in days",readonly=False)
        #expiration_tolerance = fields.Integer("Expiration Tolerance days",readonly=False)
        #partial_ordering = fields.Boolean("Allow Partial Ordering?",readonly=False)
        #partial_UOM = fields.Integer("Allow Partial UOM?",readonly=False)
        #length_of_hold = fields.Date("Lenght Of Holding",readonly=False)
        #customer_id = fields.One2many('res.partner', string='GlobalPrioritization',required=True)
        #is_gobal=fields.Boolean(" Is Customer Level Prioritization?",readonly=False)