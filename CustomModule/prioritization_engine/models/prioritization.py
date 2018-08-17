# -*- coding: utf-8 -*-
#from addons.sale.models.sale import SaleOrder
from odoo import models, fields
import logging
from dateutil.relativedelta import relativedelta
from datetime import datetime
from operator import attrgetter


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

    # Get Customer Requests
    def get_customer_requests(self):
        sps_customer_requests = self.env['sps.customer.requests'].search([('status','in',('Inprocess','Incomplete','Partial','Unprocessed','InCoolingPeriod','New'))])

        customer_product_priority_list = []

        for customer_request in sps_customer_requests:
            _logger.info("\n------------------New Customer Record---------------------"+ str(customer_request.customer_id))

            # check customer prioritization setting True/False
            res_partner = self.env['res.partner'].search([('id','=', customer_request.customer_id)])
            _logger.info("res_partner.id(customer_id) : " + str(res_partner.id) + " prioritization_setting_flag : " + str(res_partner.prioritization))

            if res_partner.prioritization is True:
                _logger.info("\nProceed.....Customer prioritization setting is True.")
                # Check product level setting or global level setting
                self.check_product_level_setting(customer_request,customer_product_priority_list)
            else:
                _logger.info("\nUnable to process because Customer prioritization setting is False.")

        # sort customer product by product/customer priority
        self.sort_product_by_priority(customer_product_priority_list)


    # Check product level setting or global level setting
    def check_product_level_setting(self, customer_request, customer_product_priority_list):
        # To check customer level setting
        customer_level_setting = self.env['prioritization_engine.prioritization'].search(
            [('customer_id', '=',customer_request.customer_id),('product_id', '=', customer_request.product_id)])

        if len(customer_level_setting) == 1:
            _logger.info(str(customer_level_setting.product_id) + ' is available in prioritization_engine_prioritization'+ str(customer_request.quantity))
            customer_product_priority_list.append(CustomerProductSetting(customer_level_setting.customer_id,
                                                                         customer_level_setting.product_id,
                                                                         customer_level_setting.priority,
                                                                         customer_level_setting.auto_allocate,
                                                                         customer_level_setting.cooling_period,
                                                                         customer_level_setting.length_of_hold,
                                                                         customer_level_setting.partial_ordering,
                                                                         customer_level_setting.expiration_tolerance,
                                                                         customer_request.quantity))

        else:
            global_level_setting = self.env['res.partner'].search(
                [('id', '=', customer_request.customer_id)])
            if len(global_level_setting) == 1:
                _logger.info(str(customer_level_setting.product_id) + ' is available in res.partner')
                customer_product_priority_list.append(CustomerProductSetting(global_level_setting.id,
                                                                             customer_request.product_id,
                                                                             global_level_setting.priority,
                                                                             global_level_setting.auto_allocate,
                                                                             global_level_setting.cooling_period,
                                                                             global_level_setting.length_of_hold,
                                                                             global_level_setting.partial_ordering,
                                                                             global_level_setting.expiration_tolerance,
                                                                             customer_request.quantity))


    # sort customer product by product/customer priority
    def sort_product_by_priority(self,customer_product_priority_list):
        customer_product_priority_list.sort(key=attrgetter('product_priority'))
        #_logger.info("customer_product_priority_list : %r" + str(customer_product_priority_list))
        for customer_product_priority in customer_product_priority_list:
            _logger.info("***** customer id : " + str(customer_product_priority.customer_id) + " Product id : " + str(customer_product_priority.product_id)
                         + " product priority" + str(customer_product_priority.product_priority))

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
            self.env['sps.customer.requests'].search([('id', '=', request_id)]).write(dict(status='InProcess'))
            return True
        else:
            # update status In cooling period
            self.env['sps.customer.requests'].search([('id', '=', request_id)]).write(dict(status='InCoolingPeriod'))
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
            self.env['sps.customer.requests'].search([('id', '=', request_id)]).write(dict(status='InProcess'))
            return True
        else:
            # update status In Process
            self.env['sps.customer.requests'].search([('id', '=', request_id)]).write(dict(status='Unprocessed'))
            return False

    # Check Expiration Tolerance in months(3/6/12)
    def check_product_expiration_tolerance(self, product_id,request_id):
        # get current datetime
        expiration_tolerance_date = datetime.today() + relativedelta(months=+int(self.get_expiration_tolerance()))
        # use_date = product expiry date
        # check lot quantity is greater than zero(0)
        stock_production_lot_quantity = self.env['stock.quant'].search(
            [('product_id', '=', 19), ('quantity', '>', 0), ('lot_id.use_date', '>=', str(expiration_tolerance_date))])

        _logger.info("stock_production_quantity : " + str(stock_production_lot_quantity.product_id) + "  " + str(
            stock_production_lot_quantity.lot_id.use_date) + "  " +
                     str(stock_production_lot_quantity.lot_id.name) + "  " + str(
            stock_production_lot_quantity.quantity))

        if len(stock_production_lot_quantity) > 0:
            _logger.info("stock available")
            # update status In Process
            self.env['sps.customer.requests'].search([('id', '=', request_id)]).write(dict(status='InProcess'))
            return True
        else:
            _logger.info("out of stock")
            # update status In Process
            self.env['sps.customer.requests'].search([('id', '=', request_id)]).write(dict(status='Unprocessed'))
            return False

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

class CustomerProductSetting:
    def __init__(self, customer_id, product_id, product_priority, auto_allocate, cooling_period, length_of_hold, partial_order, expiration_tolerance, product_quantity):
        self.customer_id = customer_id
        self.product_id = product_id
        self.product_priority = product_priority
        self.auto_allocate = auto_allocate
        self.cooling_period = cooling_period
        #self.last_purchased_date = last_purchased_date
        self.length_of_hold = length_of_hold
        self.partial_order = partial_order
        self.expiration_tolerance = expiration_tolerance
        self.product_quantity = product_quantity
