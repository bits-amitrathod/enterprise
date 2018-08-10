# -*- coding: utf-8 -*-
#from addons.sale.models.sale import SaleOrder
from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from datetime import datetime


_logger = logging.getLogger(__name__)

# Customer Global level setting
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
    sales_channel = fields.Selection([('1','Manual'),('2','Prioritization Engine')], String="Sales Channel",readonly=False)# get team id = sales channel like 3 = Manual, 4 = Prioritization Engine

    _sql_constraints = [
        ('prioritization_engine_company_uniq', 'unique(customer_id,product_id)', 'Product must be unique for customer!!!!'),
    ]

    # calculate cooling period
    def calculate_cooling_priod_in_days(self, confirmation_date, request_id):
        # get current datetime
        current_datetime = datetime.datetime.now()

        # calculate datetime difference.
        duration = current_datetime - confirmation_date  # For build-in functions
        duration_in_seconds = duration.total_seconds()  # Total number of seconds between dates
        duration_in_hours = duration_in_seconds / 3600  # Total number of hours between dates
        duration_in_days = duration_in_hours / 24
        _logger.info("duration_in_days is " + str(duration_in_days))
        if int(self.get_cooling_period()) < int(duration_in_days):
            # update status In Process
            self.env['sps.customer.requests'].write(dict(status='InProcess')).search([('id', '=', request_id)])
            return True
        else:
            # update status In cooling period
            self.env['sps.customer.requests'].write(dict(status='InCoolingPeriod')).search([('id', '=', request_id)])
            return False

    # calculate length of hold(In hours)
    def calculate_length_of_holds_in_hours(self, create_date, request_id):
        # get current datetime
        current_datetime = datetime.datetime.now()

        # calculate datetime difference.
        duration = current_datetime - create_date  # For build-in functions
        duration_in_seconds = duration.total_seconds()  # Total number of seconds between dates
        duration_in_hours = duration_in_seconds / 3600  # Total number of hours between dates
        print("duration_in_hours is " + str(duration_in_hours))
        if int(self.get_length_of_hold()) < int(duration_in_hours):
            # update status In Process
            self.env['sps.customer.requests'].write(dict(status='InProcess')).search([('id', '=', request_id)])
            return True
        else:
            # update status In Process
            self.env['sps.customer.requests'].write(dict(status='Unprocessed')).search([('id', '=', request_id)])
            return False

    # Check Expiration Tolerance in months(3/6/12)
    def check_product_expiration_tolerance(self, product_id,request_id):
        # get current datetime
        expiration_tolerance_date = date.today() + relativedelta(months=+int(self.get_expiration_tolerance()))
        # use_date = product expiry date
        stock_production_lot = self.env['stock.production.lot'].search(
            [('product_id', '=', product_id), ('use_date', '>=', expiration_tolerance_date)])

        if len(stock_production_lot):
            _logger.info("stock available")
            # update status In Process
            self.env['sps.customer.requests'].write(dict(status='InProcess')).search([('id', '=', request_id)])
            return True
        else:
            _logger.info("out of stock")
            # update status In Process
            self.env['sps.customer.requests'].write(dict(status='Unprocessed')).search([('id', '=', request_id)])
            return False


    # Return product threshold return type Integer
    def get_product_threshold(self):
        return self.threshold

    # Return product priority threshold return type Integer
    def get_product_priority(self):
        return self.priority

    # Return cooling period in days return type Integer
    def get_cooling_period(self,customer_id,product_id):
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

    # Return sales_channel return type Integer
    def get_sales_channel(self):
        return self.sales_channel

    # parameter product id
    def get_product_last_purchased_date(self, product_id):
        _logger.info("In get_product_last_purchased_date()")
        sale_orders_line = self.env['sale.order.line'].search([('product_id', '=', product_id)])

        sorted_sale_orders_line = sorted([line for line in sale_orders_line if line.order_id.confirmation_date],
                                         key=Customer._sort_by_confirmation_date, reverse=True)

        sorted_sale_orders_line.pop(1)  # get only first record
        _logger.info("^^^^" + str(sorted_sale_orders_line.order_id) + str(
            sorted_sale_orders_line.order_id.confirmation_date) + str(sorted_sale_orders_line.product_id))
        self.calculate_cooling_priod_in_days(sorted_sale_orders_line.order_id.confirmation_date)

    @staticmethod
    def _sort_by_confirmation_date(sale_order_dict):
        if sale_order_dict.order_id.confirmation_date:
            return datetime.strptime(sale_order_dict.order_id.confirmation_date, '%Y-%m-%d %H:%M:%S')

    # get product create date for to calculate length of hold parameter product id
    def get_product_create_date(self, product_id):
        _logger.info("In get_product_create_date()")
        sale_orders_line = self.env['sale.order.line'].search([('product_id', '=', product_id)])

        sorted_sale_orders_line = sorted([line for line in sale_orders_line if line.order_id.create_date], key=Customer._sort_by_create_date, reverse=True)

        sorted_sale_orders_line.pop(1) #get only first record
        _logger.info("^^^^"+ str(sorted_sale_orders_line.order_id) + str(sorted_sale_orders_line.order_id.create_date) + str(sorted_sale_orders_line.product_id))
        self.calculate_length_of_holds_in_hours(sorted_sale_orders_line.order_id.create_date)

    @staticmethod
    def _sort_by_create_date(sale_order_dict):
        if sale_order_dict.order_id.create_date:
            return datetime.strptime(sale_order_dict.order_id.create_date, '%Y-%m-%d %H:%M:%S')

    # Change date format to calculate date difference (2018-06-25 23:08:15) to (2018, 6, 25, 23, 8, 15)
    def change_date_format(self, date):
        formatted_date = date.replace("-", ",").replace(" ", ",").replace(":", ",")
        return formatted_date


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
