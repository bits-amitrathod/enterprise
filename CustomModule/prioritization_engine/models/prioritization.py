# -*- coding: utf-8 -*-
#from addons.sale.models.sale import SaleOrder
from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError

# Global level setting
class Customer(models.Model):
    _inherit = 'res.partner'
    prioritization = fields.Boolean("Prioritization setting")
    sku_preconfig=fields.Char("SKU PreConfig")
    sku_postconfig = fields.Char("SKU PostConfig")
    prioritization_ids = fields.Many2many('prioritization_engine.prioritization', 'customer_id')
    sps_sku = fields.Char("SPS SKU", readonly=False)
    threshold_min = fields.Integer("Product Min Threshold", readonly=False)
    threshold_max = fields.Integer("Product Max Threshold", readonly=False)
    priority = fields.Integer("Product Priority", readonly=False)
    cooling_period = fields.Integer("Cooling Period in days", readonly=False)
    auto_allocate = fields.Boolean("Allow Auto Allocation?", readonly=False)
    length_of_hold = fields.Integer("Length Of Hold in hours", readonly=False)
    expiration_tolerance = fields.Integer("Expiration Tolerance in months", readonly=False)
    partial_ordering = fields.Boolean("Allow Partial Ordering?", readonly=False)
    partial_UOM = fields.Boolean("Allow Partial UOM?", readonly=False)
    order_ids = fields.One2many('sale.order', 'partner_id')
    gl_account=fields.Char("GL Account")
    on_hold= fields.Boolean("On Hold")
    is_broker=fields.Boolean("Is a Broker?")
    carrier_info=fields.Char("Carrier Info")
    carrier_acc_no = fields.Char("Carrier Account No")
    quickbook_id=fields.Char("Quickbook Id")
    having_carrier = fields.Boolean("Having Carrier?")
    notification_email=fields.Char("Notification Email")

    # Return Customer prioritization setting ON(True)/OFF(False).
    def get_prioritization_setting(self):
        return self.prioritization

    # Return product minimum threshold return type Integer
    def get_product_min_threshold(self):
        return self.threshold_min

    # Return product maximum threshold return type Integer
    def get_product_max_threshold(self):
        return self.threshold_max

    # Return product priority threshold return type Integer
    def get_product_priority(self):
        return self.priority

    # Return cooling period in days return type Integer
    def get_cooling_period(self):
        return self.cooling_period

    # Return Allow Auto Allocation? True/ False
    def is_auto_allocate(self):
        return self.auto_allocate

    # Return Length Of Hold in hours return type Integer
    def get_length_of_hold(self):
        return self.length_of_hold

    # Return Expiration Tolerance in months return type Integer
    def get_expiration_tolerance(self):
        return self.expiration_tolerance

    # Return partial_ordering? True/ False
    def is_partial_ordering(self):
        return self.partial_ordering

    # Return Allow Partial UOM? True/ False
    def is_allow_partial_uom(self):
        return self.partial_UOM

    # Return GL Account return type character
    def get_gl_account(self):
        return self.gl_account

    # Return On Hold? True/ False
    def is_on_hold(self):
        return self.on_hold

    # Return Is a Broker? True/ False
    def is_is_broker(self):
        return self.is_broker

    # Return Having Carrier? True/ False
    def is_having_carrier(self):
        return self.having_carrier

    # Return Carrier Account No return type character
    def get_carrier_acc_no(self):
        return self.carrier_acc_no

    # Return Carrier Information return type character
    def get_carrier_info(self):
        return self.carrier_info


    # Return Quickbook Id return type character
    def get_quickbook_id(self):
        return self.quickbook_id

    # Return notification_email return type character
    def get_notification_email(self):
        return self.notification_email





class ProductTemplate(models.Model):
    _inherit = 'product.template'
    tier = fields.Selection([
        ('1', 'I'),
        ('2', 'II')], string='TIER Type')
    location = fields.Char("Location")
    class_code = fields.Char("Class Code")


# Customer product level setting
class Prioritization(models.Model):
    _name = 'prioritization_engine.prioritization'
    _inherits = {'product.product':'product_id'}
    sps_sku = fields.Char("SPS SKU",readonly=False)
    threshold = fields.Integer("Product Threshold",readonly=False)
    priority = fields.Integer("Product Priority",readonly=False)
    cooling_period = fields.Integer("Cooling Period in days",readonly=False)
    auto_allocate = fields.Boolean("Allow Auto Allocation?",readonly=False)
    length_of_hold = fields.Integer("Length Of Hold in hours",readonly=False)
    expiration_tolerance = fields.Integer("Expiration Tolerance in months",readonly=False)
    partial_ordering = fields.Boolean("Allow Partial Ordering?",readonly=False)
    partial_UOM = fields.Boolean("Allow Partial UOM?",readonly=False)
    length_of_holding = fields.Date("Length Of Holding",readonly=False)
    customer_id = fields.Many2one('res.partner', string='GlobalPrioritization',required=True)
    product_id = fields.Many2one('product.product', string='Prioritization Product',required=True)
    _sql_constraints = [
        ('prioritization_engine_company_uniq', 'unique(customer_id,product_id)', 'Product must be unique for customer!!!!'),
    ]

    # Return product threshold return type Integer
    def get_product_threshold(self):
        return self.threshold

    # Return product priority threshold return type Integer
    def get_product_priority(self):
        return self.priority

    # Return cooling period in days return type Integer
    def get_cooling_period(self):
        return self.cooling_period

    # Return Allow Auto Allocation? True/ False
    def is_auto_allocate(self):
        return self.auto_allocate

    # Return Length Of Hold in hours return type Integer
    def get_length_of_hold(self):
        return self.length_of_hold

    # Return Expiration Tolerance in months return type Integer
    def get_expiration_tolerance(self):
        return self.expiration_tolerance

    # Return partial_ordering? True/ False
    def is_partial_ordering(self):
        return self.partial_ordering

    # Return Allow Partial UOM? True/ False
    def is_allow_partial_uom(self):
        return self.partial_UOM

    # Return customer id return type Integer
    def get_customer_id(self):
        return self.customer_id

    # Return product id return type Integer
    def get_product_id(self):
        return self.product_id




