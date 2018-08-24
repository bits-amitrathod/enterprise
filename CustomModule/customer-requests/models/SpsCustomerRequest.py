# -*- coding: utf-8 -*-

from odoo import models, fields, api
from operator import attrgetter

_logger = logging.getLogger(__name__)

class SpsCustomerRequest(models.Model):

    _name = 'sps.customer.requests'

    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    document_id = fields.Many2one('sps.cust.uploaded.documents', string='Document', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=False, default=0)

    customer_sku = fields.Char()
    sps_sku = fields.Char()
    status = fields.Char()
    un_mapped_data = fields.Text()
    contact_id = fields.Integer()

    vendor_pricing = fields.Char()
    quantity = fields.Integer()
    required_quantity = fields.Integer()
    frequency_of_refill = fields.Integer()
    threshold = fields.Integer()
    uom = fields.Char()

    product_priority = fields.Integer(store=False)
    auto_allocate = fields.Boolean(store=False)
    cooling_period = fields.Integer(store=False)
    length_of_hold = fields.Integer(store=False)
    partial_order = fields.Boolean(store=False)
    expiration_tolerance = fields.Integer(store=False)

    # Get Customer Requests
    def get_customer_requests(self):
        sps_customer_requests = self.env['sps.customer.requests'].search(
            [('status', 'in', ('Inprocess', 'Incomplete', 'Partial', 'Unprocessed', 'InCoolingPeriod', 'New'))])

        for customer_request in sps_customer_requests:
            _logger.info(
                "\n------------------New Customer Record---------------------" + str(customer_request.customer_id))
            # check customer prioritization setting True/False
            res_partner = self.env['res.partner'].search([('id', '=', customer_request.customer_id)])
            _logger.info(
                "res_partner.id(customer_id) : " + str(res_partner.id) + " prioritization_setting_flag : " + str(
                    res_partner.prioritization))

            if res_partner.prioritization is True:
                _logger.info("\nProceed.....Customer prioritization setting is True.")
                # Check customer or global level setting
                self.check_product_level_setting(customer_request)
            else:
                _logger.info("\nUnable to process because Customer prioritization setting is False.")

        sps_customer_requests.sort(key=attrgetter('product_priority'))
        # call Product allocation by priority
        prioritization_model = self.env['prioritization_engine.prioritization'].search(
            [('customer_id', '=', customer_request['customer_id']),
             ('product_id', '=', customer_request['product_id'])])
        prioritization_model.product_allocation_by_priority(sps_customer_requests)

    # Check customer or global level setting
    def check_product_level_setting(self, customer_request):
        # To check customer level setting
        _logger.info('customer_request %r ', customer_request)

        _setting_object = self._get_settings_object(customer_request)
        _logger.info(str(_setting_object.product_id) + ' '+ str(customer_request['quantity']))

        if len(_setting_object) == 1:
            customer_request.product_priority = _setting_object.priority
            customer_request.auto_allocate = _setting_object.auto_allocate
            customer_request.cooling_period = _setting_object.cooling_period
            customer_request.length_of_hold = _setting_object.length_of_hold
            customer_request.partial_order = _setting_object.partial_ordering
            customer_request.expiration_tolerance = _setting_object.expiration_tolerance

    def _get_settings_object(self, customer_request):
        customer_level_setting = self.env['prioritization_engine.prioritization'].search(
            [('customer_id', '=', customer_request['customer_id']),
             ('product_id', '=', customer_request['product_id'])])
        if len(customer_level_setting) == 1:
            return customer_level_setting
        else:
            global_level_setting = self.env['res.partner'].search(
                [('id', '=', customer_request['customer_id'])])
            return global_level_setting

    # sort customer product by product/customer priority
    def sort_product_by_priority(self, sps_customer_requests):
        sps_customer_requests.sort(key=attrgetter('product_priority'))
