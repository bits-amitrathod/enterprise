# -*- coding: utf-8 -*-
from multiprocessing import Value

from odoo import models, fields, api, SUPERUSER_ID
import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class VendorOffer(models.Model):
    _name = 'purchase.order'
    _description = "Vendor Offer"
    _inherit = "purchase.order"
    # Fields on the list

    appraisal_no =fields.Char(string='Appraisal No#')
    acq_user_id = fields.Many2one('res.users',string='Acq Manager')
    facility = fields.Char(string='Facility')
    offer_amount = fields.Char(string='Offer Amount')
    retail_amt = fields.Char(string='Retail Amt')
    date_offered = fields.Datetime(string='Date Offered', default=fields.Datetime.now)
    revision = fields.Char(string='Revision')
    max = fields.Char(string='Max', readonly=True)
    accepted_date = fields.Datetime(string="Accepted Date")
    declined_date = fields.Datetime(string="Declined Date")

    possible_competition = fields.Selection([
        ('10', 'HEAVY COMPETITION(10 %)'),
        ('12', 'LITE COMPETITION(12 %)'),
        ('15', 'MAX OFFER(15 %)'),
        ('5', 'MODERATE COMPETITION(5 %)'),
        ('-5', 'NO COMPETITION(-5 %)'),
        ('0', 'POSSIBLE COMPETITION(0 %)'),
        ('20', 'WHOLESALER(20 %)'),
        ('12', 'HEAVIER COMPETITION(12 %)')
    ], string='Possible Competition')

    offer_type = fields.Selection([
        ('cash', 'Cash'),
        ('credit', 'Credit')
    ], string='Offer Type')

    accelerator = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
        ], string='Accelerator')
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')], string='Priority')

    new_customer = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string='New Customer')

    shipping_label_issued = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string='Shipping label Issued')

    products = fields.One2many('purchase.order.line', 'products_list', string='Order Lines')
    state = fields.Selection([
        ('ven_draft', 'Vendor Offer'),
        ('ven_sent', 'Vendor Offer Sent'),
        ('ven_cancel', 'Cancelled'),
        ('purchase', 'Purchase')
    ], string='Status', readonly=True, index=True, copy=False, default='ven_draft', track_visibility='onchange', store=False)

    # @api.model_cr
    # def init(self):
    #     self.write({'state': 'ven_draft'})
    #     self.date_offered=datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    @api.multi
    def action_send_offer_email(self):
        pass

    @api.multi
    def action_print_vendor_offer(self):
        pass

    @api.multi
    def action_confirm_vendor_offer(self,vals):
        PurchaseOrder = self.env['purchase.order']
        self.write({'state': 'purchase'})
        vals['notes'] = 'aa'
        return PurchaseOrder.create(vals)

    @api.multi
    def action_cancel_vendor_offer(self):
        self.write({'state': 'cancel'})


class VendorOfferProduct(models.Model):
    _name = 'purchase.order.line'
    _inherit = "purchase.order.line"
    _description = "Vendor Offer Product"

    product_tier = fields.Char(string="TIER")
    product_sales_count = fields.Char(string="Sales Count All")
    product_sales_count_month = fields.Char(string="Sales Count Month")
    product_sales_count_90 = fields.Char(string="Sales Count 90 Days")
    product_sales_count_yrs = fields.Char(string="Sales Count Yrs")
    qty_in_stock = fields.Char(string="Quantity In Stock")
    expired_inventory = fields.Char(string="Expired Inventory Items")
    multiplier = fields.Char(string="Multiplier",store=False)
    offer_price = fields.Char(string="Offer Price")
    margin = fields.Char(string="Margin")
    manufacturer = fields.Char(string="Manufacturer",store=False)
    total_retail = fields.Char(string="Total Retail")
    total_offer = fields.Char(string="Total Offer")
    products_list = fields.Many2one('purchase.order',  string='Order Lines')

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date(string="End Date", required=True)

    @api.onchange('product_id')
    def onchange_product_id_vendor_offer(self):
        result1 = {}
        if not self.product_id:
            return result1

        self.qty_in_stocks()
        groupby_dict = {}
        groupby_dict_month = {}
        sale_orders_line = self.env['sale.order.line'].search([('product_id', '=', self.product_id.id)])
        groupby_dict['data'] = sale_orders_line
        total = 0
        for sale_order in groupby_dict['data']:
            total=total + sale_order.price_total

        self.product_sales_count=total
        print('------------------------------------------------------------------------------------')
        sale_orders = self.env['sale.order'].search([('product_id', '=', self.product_id.id)])
        print(sale_orders)
        filtered_by_date = list(
                    filter(lambda x: datetime.datetime.strptime(x.date_order, "%Y-%m-%d %H:%M:%S") >= (datetime.datetime.now()- datetime.timedelta(days=30)), sale_orders))
        filtered_order_month=filtered_by_date
        print(filtered_order_month)
        groupby_dict_month['data'] = filtered_order_month

        print('------------------------------------------------------------------------------------')


    @api.onchange('multiplier','product_sales_count','qty_in_stock')
    def cal_all_val(self):
        self.sales_total =  float(self.qty_in_stock) * float(self.price_unit)

    @api.multi
    def qty_in_stocks(self):
        domain = [
            ('product_id', '=',  self.product_id.id),
        ]
        moves = self.env['stock.move'].search(domain,limit=1)
        self.qty_in_stock=moves.product_qty