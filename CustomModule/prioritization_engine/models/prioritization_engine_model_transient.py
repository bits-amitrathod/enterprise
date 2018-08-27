from odoo import models, fields, api
import logging
from dateutil.relativedelta import relativedelta
from datetime import datetime
from operator import attrgetter

_logger = logging.getLogger(__name__)

class PrioritizationEngineModel(models.Model):
    _name = "prioritization.engine.model"

    sps_customer_request = fields.Many2one('sps.customer.requests', string='Customer Request')

    product_priority = fields.Integer(store=False)
    auto_allocate = fields.Boolean(store=False)
    cooling_period = fields.Integer(store=False)
    length_of_hold = fields.Integer(store=False)
    partial_order = fields.Boolean(store=False)
    expiration_tolerance = fields.Integer(store=False)

    def allocate_product_by_priority(self, pr_models):
        _logger.info('In product_allocation_by_priority')
        for prioritization_engine_model in pr_models:
            # 1) Auto Allocate True/False
            # customer_product.auto_allocate==true

            if self.auto_allocate:
                # 2) get available production lot list.
                production_lot_list = self.get_available_production_lot_list(
                    prioritization_engine_model.sps_customer_request)
                _logger.info('In ++++++++++++++++%r', production_lot_list)
                if len(production_lot_list) >= 1:
                    # 3) check cooling period- method return True/False
                    if self.calculate_cooling_priod_in_days(prioritization_engine_model.sps_customer_request):
                        _logger.info('successed cooling period')
                        if self.calculate_length_of_holds_in_hours(prioritization_engine_model.sps_customer_request):
                            _logger.info('successed length of hold')
                            # allocate product
                            product_allocation_flag = self.allocate_product(
                                prioritization_engine_model.sps_customer_request, production_lot_list)
                            if product_allocation_flag is False:
                                # check partial order flag is True or False
                                if prioritization_engine_model.partial_ordering is True:
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
    def get_available_production_lot_list(self, sps_customer_request):
        _logger.info('expiration_tolerance %r', self.expiration_tolerance)
        production_lot_list = self.env['stock.quant'].search(
            [('product_id', '=', sps_customer_request.product_id.id), ('quantity', '>', 0),
             ('location_id.usage', '=', 'internal'), ('location_id.active', '=', 'true')])
        _logger.info('production_lot_list ^^^^^: %r', production_lot_list)
        production_lot_list_to_be_returned = []
        for production_lot in production_lot_list:
            if production_lot.lot_id and production_lot.lot_id.life_date:
                if datetime.strptime(production_lot.lot_id.life_date,
                                     '%Y-%m-%d %H:%M:%S') >= self.get_product_expiration_tolerance_date():
                    production_lot_list_to_be_returned.append(production_lot)
        # sort list by latest expiry date(life date)
        production_lot_list_to_be_returned.sort(key=attrgetter('lot_id.life_date'))
        return production_lot_list_to_be_returned

    # calculate cooling period
    def calculate_cooling_priod_in_days(self, sps_customer_request):
        # get product last purchased date
        confirmation_date = self.get_product_last_purchased_date(sps_customer_request)
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
                self.env['sps.customer.requests'].search([('id', '=', sps_customer_request.id)]).write(dict(status='InCoolingPeriod'))
                return False
        else:
            return True

    # calculate length of hold(In hours)
    def calculate_length_of_holds_in_hours(self, sps_customer_request):
        # get product create date
        create_date = self.get_product_create_date(sps_customer_request)

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
                self.env['sps.customer.requests'].search([('id', '=', sps_customer_request.id)]).write(dict(status='Unprocessed'))
                return False
        else:
            return True

    # get product expiration tolerance date
    def get_product_expiration_tolerance_date(self):
        # expiration tolerance in months(3/6/12)
        expiration_tolerance_date = datetime.today() + relativedelta(months=+int(self.expiration_tolerance))
        return expiration_tolerance_date

    # Allocate product
    def allocate_product(self, sps_customer_request, production_lot_list):
        product_allocation_flag = False
        for production_lot in production_lot_list:
            if production_lot.quantity >= sps_customer_request.required_quantity:
                _logger.info('product allocated from lot %r %r %r', production_lot.lot_id, production_lot.quantity,
                            sps_customer_request.required_quantity)
                self.env['stock.quant'].search([('id', '=', production_lot.id)]).write(
                    dict(quantity=production_lot.quantity - sps_customer_request.required_quantity))
                _logger.info('Quantity Updated')
                product_allocation_flag = True
                self.env['sps.customer.requests'].search([('id', '=', sps_customer_request.id)]).write(
                    dict(status='Completed'))
                break
        return product_allocation_flag


    # Allocate partial order product
    def allocate_partial_order_product(self, sps_customer_request, production_lot_list):
        required_product_quantity = sps_customer_request.required_quantity
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
            _logger.info("Allocated Partial order of product id " + str(
                    sps_customer_request.product_id.id) + ". Total required product quantity is " + str(
                    sps_customer_request.required_product_quantity))
            self.env['sps.customer.requests'].search([('id', '=', sps_customer_request.id)]).write(
                    dict(status='Completed'))
        elif required_product_quantity > 0:
            allocated_product_quantity = int(sps_customer_request.required_quantity) - int(
                    required_product_quantity)
            _logger.info(str(" We have allocated only " + str(allocated_product_quantity) + " products. " + str(
                    required_product_quantity) + " are pending."))
            self.env['sps.customer.requests'].search([('id', '=', sps_customer_request.id)]).write(
                    dict(status='Partial'))

    # get product last purchased date, parameter product id
    def get_product_last_purchased_date(self, sps_customer_request):
        _logger.info("In get_product_last_purchased_date()")
        sale_orders_line = self.env['sale.order.line'].search([('product_id', '=', sps_customer_request.product_id.id)])
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
    def get_product_create_date(self, sps_customer_request):
        _logger.info("In get_product_create_date()")
        sale_orders_line = self.env['sale.order.line'].search([('product_id', '=', sps_customer_request.product_id.id)])

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
