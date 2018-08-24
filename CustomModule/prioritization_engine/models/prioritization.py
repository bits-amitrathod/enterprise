# -*- coding: utf-8 -*-
#from addons.sale.models.sale import SaleOrder
from odoo import models, fields, api,_
from odoo.exceptions import UserError, AccessError
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
    expiration_tolerance = fields.Integer("Expiration Tolerance in Months", readonly=False)

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
    preferred_method=fields.Selection([
       ('mail', 'Mail'),
       ('email', 'E Mail'),
       ('both', 'E Mail & Mail ')], string='Preferred Invoice Delivery Method')
    shipping_terms = fields.Selection([
        ('1', 'Prepaid & Billed'),
        ('2', 'Prepaid'),
        (3,'Freight Collect')], string='Shipping Terms')

    @api.model
    def create(self, vals):
        self.on_hold_changes(vals)
        return super(Customer, self).create(vals)

    @api.multi
    def write(self, vals):
        res = super(Customer, self).write(vals)
        self.on_hold_changes(vals)
        return res

    def on_hold_changes(self, vals):
        for child_id in self.child_ids:
            print(child_id.on_hold);
            child_id.write({'on_hold':self.on_hold});
            print(child_id.on_hold)

    def action_view_notification(self):
        '''
        This function returns an action that display existing notification
        of given partner ids. It can be form
        view,
        '''
        action = self.env.ref('prioritization_engine.action_notification_setting').read()[0]
        action['views'] = [(self.env.ref('prioritization_engine.view_notification_setting_form').id, 'form')]
        action['view_ids'] = self.env.ref('prioritization_engine.view_notification_setting_form').id
        action['res_id'] = self.id
        #print("Inside  action_view_notification")
        return action

    def get_customer_request(self):
        _logger.info("***************In main function()**************")
        self = self.env['prioritization_engine.prioritization'].search([('customer_id', '=', 5)])
        if self.customer_id:
            return self.get_customer_requests()

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    location = fields.Char("Location")
    premium = fields.Boolean("Premium")
    sku_code = fields.Char('SKU / Catalog No')
    manufacturer_pref = fields.Char(string='Manuf. Catalog No')


class NotificationSetting(models.Model):
    _inherit = 'res.partner'

    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    monday = fields.Boolean("Monday")
    tuesday = fields.Boolean("Tuesday")
    wednesday = fields.Boolean("Wednesday")
    thursday = fields.Boolean("Thursday")
    friday = fields.Boolean("Friday")
    saturday = fields.Boolean("Saturday")
    sunday = fields.Boolean("Sunday")

# Customer product level setting
class Prioritization(models.Model):
    _name = 'prioritization_engine.prioritization'
    _inherits = {'product.product':'product_id'}
    #sps_sku = fields.Char("SPS SKU",readonly=False)
    min_threshold = fields.Integer("Min Threshold",readonly=False)
    max_threshold = fields.Integer("Max Threshold",readonly=False)
    priority = fields.Integer("Product Priority",readonly=False)
    cooling_period = fields.Integer("Cooling Period in days",readonly=False)
    auto_allocate = fields.Boolean("Allow Auto Allocation?",readonly=False)
    length_of_hold = fields.Integer("Length Of Hold in hours",readonly=False)
    expiration_tolerance = fields.Integer("Expiration Tolerance in months",readonly=False)
    partial_ordering = fields.Boolean("Allow Partial Ordering?",readonly=False)
    partial_UOM = fields.Boolean("Allow Partial UOM?",readonly=False)
    length_of_holding = fields.Integer("Length Of Holding",readonly=False)
    customer_id = fields.Many2one('res.partner', string='GlobalPrioritization',required=True)
    product_id = fields.Many2one('product.product', string='Product',required=True)
    sales_channel = fields.Selection([('1','Manual'),('2','Prioritization Engine')], String="Sales Channel",readonly=False)# get team id = sales channel like 3 = Manual, 4 = Prioritization Engine

    _sql_constraints = [
        ('prioritization_engine_company_uniq', 'unique(customer_id,product_id)', 'Product must be unique for customer!!!!'),
    ]

    # Product allocation by priority
    def product_allocation_by_priority(self,customer_product_priority_list, customer_request):
        _logger.info('In product_allocation_by_priority')
        for customer_product in customer_product_priority_list:
            _logger.info(
                "\ncustomer_id  product_id  product_priority  auto_allocate  cooling_period  length_of_hold  partial_order  expiration_tolerance  Required Product Quantity\n")
            _logger.info("\n"+str(customer_product.customer_id)+"   "+str(customer_product.product_id)+"  "+str(customer_product.product_priority)+"  "+str(customer_product.auto_allocate)+
                         "   " + str(customer_product.cooling_period) +"   " + str(customer_product.length_of_hold) +"   " + str(customer_product.partial_order)+
                         "   " + str(customer_product.expiration_tolerance) + "   " + str(customer_product.required_product_quantity))

            # 1) Auto Allocate True/False
            if self.auto_allocate is True:
                #2) get available production lot list.
                production_lot_list = self.get_available_production_lot_list(customer_product)
                _logger.info('In ++++++++++++++++%r', production_lot_list)
                if len(production_lot_list) >= 1:
                    # 3) check cooling period- method return True/False
                    if self.calculate_cooling_priod_in_days(customer_request):
                        _logger.info('successed cooling period')
                        if self.calculate_length_of_holds_in_hours(customer_request):
                            _logger.info('successed length of hold')
                            # allocate product
                            product_allocation_flag = self.allocate_product(customer_product, production_lot_list)
                            if product_allocation_flag is False:
                                # check partial order flag is True or False
                                if self.partial_ordering is True:
                                    _logger.info('Partial ordering flag is True')
                                else:
                                    _logger.info('Partial ordering flag is False')
                    else:
                        _logger.info('In cooling period.....')
                else:
                    _logger.info('Quantity not available')
            else:
                _logger.info('Auto allocate is false....')

    # get available production lot list, parameter product id.
    def get_available_production_lot_list(self, customer_product):
        production_lot_list = self.env['stock.quant'].search(
             [('product_id', '=', customer_product.product_id.id),('quantity', '>', 0),
              ('location_id.usage', '=', 'internal'),('location_id.active', '=', 'true')])
        _logger.info('production_lot_list ^^^^^: %r', production_lot_list)
        production_lot_list_to_be_returned = []
        for production_lot in production_lot_list:
            if production_lot.lot_id and production_lot.lot_id.life_date:
                if datetime.strptime(production_lot.lot_id.life_date, '%Y-%m-%d %H:%M:%S') >= self.get_product_expiration_tolerance_date():
                    production_lot_list_to_be_returned.append(production_lot)
        # sort list by latest expiry date(life date)
        production_lot_list_to_be_returned.sort(key=attrgetter('lot_id.life_date'))
        return production_lot_list_to_be_returned

    # calculate cooling period
    def calculate_cooling_priod_in_days(self, customer_request):
        # get product last purchased date
        confirmation_date = self.get_product_last_purchased_date()
        if not confirmation_date is None:
            # get current datetime
            current_datetime = datetime.datetime.now()

            # calculate datetime difference.
            duration = current_datetime - confirmation_date  # For build-in functions
            duration_in_seconds = duration.total_seconds()  # Total number of seconds between dates
            duration_in_hours = duration_in_seconds / 3600  # Total number of hours between dates
            duration_in_days = duration_in_hours / 24
            _logger.info("duration_in_days is " + str(duration_in_days))
            if int(self.cooling_period) < int(duration_in_days):
                return True
            else:
                # update status In cooling period
                self.env['sps.customer.requests'].search([('id', '=', customer_request.id)]).write(dict(status='InCoolingPeriod'))
                return False
        else:
            return True

    # calculate length of hold(In hours)
    def calculate_length_of_holds_in_hours(self, customer_request):
        # get product create date
        create_date = self.get_product_create_date()

        if not create_date is None:
            # get current datetime
            current_datetime = datetime.datetime.now()
            # calculate datetime difference.
            duration = current_datetime - create_date  # For build-in functions
            duration_in_seconds = duration.total_seconds()  # Total number of seconds between dates
            duration_in_hours = duration_in_seconds / 3600  # Total number of hours between dates
            _logger.info("duration_in_hours is " + str(duration_in_hours))
            if int(self.length_of_hold) < int(duration_in_hours):
                return True
            else:
                # update status In Process
                self.env['sps.customer.requests'].search([('id', '=', customer_request.id)]).write(dict(status='Unprocessed'))
                return False
        else:
            return True

    # get product expiration tolerance date
    def get_product_expiration_tolerance_date(self):
        # expiration tolerance in months(3/6/12)
        expiration_tolerance_date = datetime.today() + relativedelta(months=+int(self.expiration_tolerance))
        return expiration_tolerance_date

        # Allocate product
        def allocate_product(self, customer_product, production_lot_list):
            product_allocation_flag = False
            for production_lot in production_lot_list:
                if production_lot.quantity >= customer_product.required_product_quantity:
                    _logger.info('product allocated from lot %r %r %r', production_lot.lot_id, production_lot.quantity,
                                 customer_product.required_product_quantity)
                    self.env['stock.quant'].search([('id', '=', production_lot.id)]).write(
                        dict(quantity=production_lot.quantity - customer_product.required_product_quantity))
                    _logger.info('Quantity Updated')
                    product_allocation_flag = True
                    self.env['sps.customer.requests'].search([('id', '=', customer_product.customer_request_id)]).write(
                        dict(status='Completed'))
                    break
            return product_allocation_flag

        # Allocate partial order product
        def allocate_partial_order_product(self, customer_product, production_lot_list):
            required_product_quantity = customer_product.required_product_quantity
            for production_lot in production_lot_list:
                if required_product_quantity >= production_lot.quantity:
                    _logger.info('product allocated from lot %r %r %r', production_lot.lot_id, production_lot.quantity,
                                 required_product_quantity)
                    required_product_quantity = int(required_product_quantity) - int(production_lot.quantity)
                    self.env['stock.quant'].search([('id', '=', production_lot.id)]).write(dict(quantity=0))
                    _logger.info('Quantity Updated')
                else:
                    if required_product_quantity < production_lot.quantity:
                        _logger.info('product allocated from lot %r %r %r', production_lot.lot_id,
                                     production_lot.quantity,
                                     required_product_quantity)
                        self.env['stock.quant'].search([('id', '=', production_lot.id)]).write(
                            dict(quantity=int(production_lot.quantity) - int(required_product_quantity)))
                        required_product_quantity = 0
                        _logger.info('Quantity Updated')

            if required_product_quantity == 0:
                print("Allocated Partial order of product id " + str(
                    customer_product.product_id.id) + ". Total required product quantity is " + str(
                    customer_product.required_product_quantity))
                self.env['sps.customer.requests'].search([('id', '=', customer_product.customer_request_id)]).write(
                    dict(status='Completed'))
            elif required_product_quantity > 0:
                allocated_product_quantity = int(customer_product.required_product_quantity) - int(
                    required_product_quantity)
                print(str(" We have allocated only " + str(allocated_product_quantity) + " products. " + str(
                    required_product_quantity) + " are pending."))
                self.env['sps.customer.requests'].search([('id', '=', customer_product.customer_request_id)]).write(
                    dict(status='Partial'))

    # get product last purchased date, parameter product id
    def get_product_last_purchased_date(self):
        _logger.info("In get_product_last_purchased_date()")
        sale_orders_line = self.env['sale.order.line'].search([('product_id', '=', self.product_id.id)])
        sorted_sale_orders_line = sorted([line for line in sale_orders_line if line.order_id.confirmation_date],
                                         key=self._sort_by_confirmation_date, reverse=True)
        if len(sorted_sale_orders_line)> 0:
            sorted_sale_orders_line.pop(1)  # get only first record
            _logger.info("^^^^" + str(sorted_sale_orders_line.order_id) + str(
                sorted_sale_orders_line.order_id.confirmation_date) + str(sorted_sale_orders_line.product_id.id))
            return sorted_sale_orders_line.order_id.confirmation_date
        else:
            return None


    @staticmethod
    def _sort_by_confirmation_date(sale_order_dict):
        if sale_order_dict.order_id.confirmation_date:
            return datetime.strptime(sale_order_dict.order_id.confirmation_date, '%Y-%m-%d %H:%M:%S')

    # get product create date for to calculate length of hold, parameter product id
    def get_product_create_date(self):
        _logger.info("In get_product_create_date()")
        sale_orders_line = self.env['sale.order.line'].search([('product_id', '=', self.product_id.id)])

        sorted_sale_orders_line = sorted([line for line in sale_orders_line if line.order_id.create_date], key=self._sort_by_create_date, reverse=True)

        if len(sorted_sale_orders_line) > 1:
            sorted_sale_orders_line.pop(1) #get only first record
            _logger.info("^^^^"+ str(sorted_sale_orders_line.order_id) + str(sorted_sale_orders_line.order_id.create_date) + str(sorted_sale_orders_line.product_id))
            return sorted_sale_orders_line.order_id.create_date
        else:
            return None


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
    min_threshold = fields.Integer("Min Threshold", readonly=False)
    max_threshold = fields.Integer("Max Threshold", readonly=False)
    priority = fields.Integer("Priority")
    cooling_period = fields.Integer("Cooling Period in days")
    auto_allocate = fields.Boolean("Allow Auto Allocation?")
    length_of_hold = fields.Integer("Length Of Hold in days")
    expiration_tolerance = fields.Integer("Expiration Tolerance days")
    partial_ordering = fields.Boolean("Allow Partial Ordering?")
    partial_UOM = fields.Boolean("Allow Partial UOM?")
    length_of_hold = fields.Integer("Lenght Of Holding")

    def action_confirm(self,arg):
        for selected in arg["selected_ids"]:
            record = self.env['prioritization_engine.prioritization'].search([('id', '=', selected)])[0]
            record.write({'min_threshold': self.min_threshold,'max_threshold': self.min_threshold,'priority': self.priority,'cooling_period': self.cooling_period,'auto_allocate': self.auto_allocate,
                        'expiration_tolerance': self.expiration_tolerance,'partial_ordering': self.partial_ordering,'partial_UOM': self.partial_UOM,
                        'length_of_hold': self.length_of_hold})
        return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

class CustomerProductSetting:
    def __init__(self, customer_request_id, customer_id, product_id, product_priority, auto_allocate, cooling_period, length_of_hold, partial_order, expiration_tolerance, product_quantity):
        self.customer_request_id = customer_request_id
        self.customer_id = customer_id
        self.product_id = product_id
        self.product_priority = product_priority
        self.auto_allocate = auto_allocate
        self.cooling_period = cooling_period
        #self.last_purchased_date = last_purchased_date
        self.length_of_hold = length_of_hold
        self.partial_order = partial_order
        self.expiration_tolerance = expiration_tolerance
        self.required_product_quantity = product_quantity
