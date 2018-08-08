# -*- coding: utf-8 -*-
#from addons.sale.models.sale import SaleOrder
from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError


class Customer(models.Model):
    _inherit = 'res.partner'
    prioritization = fields.Boolean("Prioritization setting" )
    sku_preconfig=fields.Char("SKU PreConfig")
    sku_postconfig = fields.Char("SKU PostConfig")
    prioritization_ids = fields.One2many('prioritization_engine.prioritization', 'customer_id')
    sps_sku = fields.Char("SPS SKU", readonly=False)
    threshold_min = fields.Integer("Product Min Threshold", readonly=False)
    threshold_max = fields.Integer("Product Max Threshold", readonly=False)
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
    is_broker=fields.Boolean("Is a Broker?")
    carrier_info=fields.Char("Carrier Info")
    carrier_acc_no = fields.Char("Carrier Account No")
    quickbook_id=fields.Char("Quickbook Id")
    having_carrier = fields.Boolean("Having Carrier ?")
    notification_email=fields.Char("Notification Email")

    #@api.multi
    def bulk_verify(self,arg):
        print(self)
        #print(arg)
        #for record in self:
            #print(record)
        view = self.env['prioritization.transient']
       # view = self.env.ref('prioritization_engine.view_form_prioritization_normal')
        view_id=self.env.ref('prioritization_engine.view_form_prioritization_normal',False).id
        params=[]
        #new = view.create(params)
        print(view_id)
        #print(new.id)
        return {
            'type': 'ir.actions.act_window',
            #'name':_('Multiple Update Operations'),
            'res_model': 'prioritization.transient',
            'view_type': 'form',
            'view_mode': 'form',
            'multi':True,
            #'res_id': new.id,
            #'view_id': view_id,
            #'target': 'new',

        }
'''show_lots_m2o=self.has_tracking != 'none' and (self.picking_type_id.use_existing_lots or self.state == 'done' or self.origin_returned_move_id.id),  # able to create lots, whatever the value of ` use_create_lots`.
                show_lots_text=self.has_tracking != 'none' and self.picking_type_id.use_create_lots and not self.picking_type_id.use_existing_lots and self.state != 'done' and not self.origin_returned_move_id.id,
                show_source_location=self.location_id.child_ids,
                show_destination_location=self.location_dest_id.child_ids,
                show_package=not self.location_id.usage == 'supplier',
                show_reserved_quantity=self.state != 'done' '''

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
        ('prioritization_engine_company_uniq', 'unique(customer_id,product_id)', 'Product must be unique for customer!!!!'),
       ]

class PrioritizationTransient(models.TransientModel):
    _name = 'prioritization.transient'
    threshold = fields.Integer("Product Threshold")
    priority = fields.Integer("Product Priority")
    cooling_period = fields.Integer("Cooling Period in days")
    auto_allocate = fields.Boolean("Allow Auto Allocation?")
    length_of_hold = fields.Integer("Length Of Hold in days")
    expiration_tolerance = fields.Integer("Expiration Tolerance days")
    partial_ordering = fields.Boolean("Allow Partial Ordering?")
    partial_UOM = fields.Integer("Allow Partial UOM?")
    length_of_hold = fields.Date("Lenght Of Holding")