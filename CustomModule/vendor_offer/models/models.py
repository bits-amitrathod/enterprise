# -*- coding: utf-8 -*-
from pygments.lexer import default

from odoo import models, fields, api, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
import datetime
import math
from decimal import Decimal, ROUND_HALF_UP


class VendorOffer(models.Model):
    # _name = 'purchase.order'
    _description = "Vendor Offer"
    _inherit = "purchase.order"

    carrier_info = fields.Char("Carrier Info", related='partner_id.carrier_info', readonly=True)
    carrier_acc_no = fields.Char("Carrier Account No", related='partner_id.carrier_acc_no', readonly=True)
    shipping_terms = fields.Selection(string='Shipping Term', related='partner_id.shipping_terms', readonly=True)
    appraisal_no = fields.Char(string='Appraisal No#')
    acq_user_id = fields.Many2one('res.users',string='Acq  Manager ')
    date_offered = fields.Datetime(string='Date Offered', default=fields.Datetime.now)
    revision = fields.Char(string='Revision ')
    max = fields.Char(string='Max', readonly=True ,default=0)
    accepted_date = fields.Datetime(string="Accepted Date")
    declined_date = fields.Datetime(string="Declined Date")
    retail_amt = fields.Monetary(string="Total Retail",readonly=True,default=0 ,compute='_amount_tot_all')
    offer_amount = fields.Monetary(string="Total  Offer",readonly=True,default=0,compute='_amount_tot_all')
    date_planned = fields.Datetime(string='Scheduled Date')
    possible_competition = fields.Many2one('competition.competition', string="Possible Competition")
    offer_type = fields.Selection([
        ('cash', 'Cash'),
        ('credit', 'Credit')
    ], string='Offer Type')

    shipping_date = fields.Datetime(string="Shipping Date")
    delivered_date = fields.Datetime(string="Delivered Date")
    expected_date = fields.Datetime(string="Expected Date")

    notes_desc = fields.Text(string="Note")

    accelerator=fields.Boolean(string="Accelerator")
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')], string='Priority')

    new_customer = fields.Boolean(string="New Customer")
    shipping_label_issued = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string='Shipping label Issued')

    status = fields.Selection([
        ('ven_draft', 'Vendor Offer'),
        ('ven_sent', 'Vendor Offer Sent'),
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='ven_draft',track_visibility='onchange',store=True)

    state = fields.Selection([
        ('ven_draft', 'Vendor Offer'),
        ('ven_sent', 'Vendor Offer Sent'),
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')

    @api.depends('order_line.offer_price')
    def _amount_tot_all(self):
        for order in self:
            retail_amt = offer_amount = 0.0
            for line in order.order_line:
                retail_amt += float(line.product_retail)
                offer_amount += float(line.offer_price)
            order.update({
                'retail_amt': retail_amt,
                'offer_amount': offer_amount,
            })

    @api.onchange('possible_competition')
    def possible_competition_onchange(self):
        self.state = 'ven_draft'
        for order in self:
            for line in order.order_line:
                multiplier_list = self.env['multiplier.multiplier'].search([('id', '=', line.multiplier.id)])
                line.margin = multiplier_list.margin
                line.offer_price = round(float(line.price_unit) * (
                            float(multiplier_list.margin) / 100 + float(self.possible_competition.id) / 100),2)

    @api.onchange('accelerator','retail_amt')
    def accelerator_onchange(self):
        print(self.accelerator)
        if self.accelerator == True:
            self.max = float(self.retail_amt)*float(0.65)
        else:
            self.max = 0
        print(self.max)

    @api.multi
    def action_send_offer_email(self):
        pass
        # self.ensure_one()
        # ir_model_data = self.env['ir.model.data']
        # try:
        #     if self.env.context.get('send_rfq', False):
        #         template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase')[1]
        #     else:
        #         template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase_done')[1]
        # except ValueError:
        #     template_id = False
        # try:
        #     compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        # except ValueError:
        #     compose_form_id = False
        # ctx = dict(self.env.context or {})
        # ctx.update({
        #     'default_model': 'purchase.order',
        #     'default_res_id': self.ids[0],
        #     'default_use_template': bool(template_id),
        #     'default_template_id': template_id,
        #     'default_composition_mode': 'comment',
        #     'custom_layout': "purchase.mail_template_data_notification_email_purchase_order",
        #     'force_email': True
        # })
        # return {
        #     'name': _('Compose Email'),
        #     'type': 'ir.actions.act_window',
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'res_model': 'mail.compose.message',
        #     'views': [(compose_form_id, 'form')],
        #     'view_id': compose_form_id,
        #     'target': 'new',
        #     'context': ctx,
        # }

    @api.multi
    def action_print_vendor_offer(self):
        pass

    @api.multi
    def action_confirm_vendor_offer(self):
        self.write({'state': 'purchase'})
        self.write({'status': 'purchase'})
        return True

    @api.multi
    def action_cancel_vendor_offer(self):
        self.write({'state': 'cancel'})
        self.write({'status': 'cancel'})

    @api.model
    def create(self, vals):
        vals['state']= 'ven_draft'
        return super(VendorOffer, self).create(vals)


class VendorOfferProduct(models.Model):

    # _name = 'purchase.order.line'
    _inherit = "purchase.order.line"
    _inherits = {'product.product': 'product_id'}
    _description = "Vendor Offer Product"

    product_tier = fields.Many2one('tier.tier', string="Tier")
    product_sales_count = fields.Char(string="Sales Count All")
    product_sales_count_month = fields.Char(string="Sales Count Month")
    product_sales_count_90 = fields.Char(string="Sales Count 90 Days")
    product_sales_count_yrs = fields.Char(string="Sales Count Yr")
    qty_in_stock = fields.Char(string="Quantity In Stock")
    prod_qty = fields.Char(string="Quantity")
    expiration_date = fields.Datetime(string="Expiration Date")
    expired_inventory = fields.Char(string="Expired Inventory Items")
    multiplier = fields.Many2one('multiplier.multiplier', string="Multiplier")
    offer_price = fields.Char(string="Total Offer Price")
    product_offer_price = fields.Char(string="Offer Price")
    margin = fields.Char(string="Margin")
    possible_competition = fields.Many2one(related='order_id.possible_competition',store=False)
    product_note = fields.Text(string="Notes")
    product_retail = fields.Char(string="Total Retail Price")
    product_unit_price = fields.Char(string="Retail Price")

    @api.onchange('product_id')
    def onchange_product_id_vendor_offer(self):
        result1 = {}
        if not self.product_id:
            return result1

        self.qty_in_stocks()
        groupby_dict = groupby_dict_month = groupby_dict_90 = groupby_dict_yr = {}
        sale_orders_line = self.env['sale.order.line'].search([('product_id', '=', self.product_id.id)])
        groupby_dict['data'] = sale_orders_line
        total = total_m = total_90 = total_yr = 0

        for sale_order in groupby_dict['data']:
            total=total + sale_order.product_uom_qty

        self.product_sales_count=total
        sale_orders = self.env['sale.order'].search([('product_id', '=', self.product_id.id)])
        date_planned = fields.Datetime(string='Scheduled Date', compute='_compute_date_planned', store=True, index=True)

        filtered_by_date = list(
                    filter(lambda x: fields.Datetime.from_string(x.date_order).date() >= (fields.date.today() - datetime.timedelta(days=30)), sale_orders))
        groupby_dict_month['data'] = filtered_by_date
        for sale_order_list in groupby_dict_month['data']:
            for sale_order in sale_order_list.order_line:
                if sale_order.product_id.id == self.product_id.id:
                    total_m=total_m + sale_order.product_uom_qty

        self.product_sales_count_month=total_m

        filtered_by_90 = list(filter(lambda x: fields.Datetime.from_string(x.date_order).date() >= (fields.date.today() - datetime.timedelta(days=90)), sale_orders))
        groupby_dict_90['data'] = filtered_by_90

        for sale_order_list_90 in groupby_dict_90['data']:
            for sale_order in sale_order_list_90.order_line:
                if sale_order.product_id.id == self.product_id.id:
                    total_90 = total_90 + sale_order.product_uom_qty

        self.product_sales_count_90 = total_90

        filtered_by_yr = list(filter(lambda x: fields.Datetime.from_string(x.date_order).date() >= (fields.date.today() - datetime.timedelta(days=365)), sale_orders))
        groupby_dict_yr['data'] = filtered_by_yr
        for sale_order_list_yr in groupby_dict_yr['data']:
            for sale_order in sale_order_list_yr.order_line:
                if sale_order.product_id.id == self.product_id.id:
                    total_yr = total_yr + sale_order.product_uom_qty

        self.product_sales_count_yrs = total_yr

        if self.tier.code == False:
            multiplier_list = self.env['multiplier.multiplier'].search([('code', '=', 'out of scope')])
            self.multiplier = multiplier_list.id
        elif self.product_sales_count == '0':
            multiplier_list = self.env['multiplier.multiplier'].search([('code', '=', 'no history')])
            self.multiplier = multiplier_list.id
        elif float(self.qty_in_stock) > (float(self.product_sales_count) * 2 ) and self.product_sales_count!='0':
            multiplier_list = self.env['multiplier.multiplier'].search([('code', '=', 'overstocked')])
            self.multiplier = multiplier_list.id
        elif self.product_id.product_tmpl_id.premium == True:
            multiplier_list = self.env['multiplier.multiplier'].search([('code', '=', 'premium')])
            self.multiplier = multiplier_list.id
        elif self.tier.code == '1':
            multiplier_list = self.env['multiplier.multiplier'].search([('code', '=', 't1 good 45')])
            self.multiplier = multiplier_list.id
        elif self.tier.code == '2':
            multiplier_list = self.env['multiplier.multiplier'].search([('code', '=', 't2 good 35')])
            self.multiplier=multiplier_list.id

        self.cal_offer_price()
        self.expired_inventory_cal()
        for order in self:
            order.env.cr.execute("SELECT min(use_date), max(use_date) FROM public.stock_production_lot where product_id =" + str(order.product_id.id))
            query_result = order.env.cr.dictfetchone()
            if query_result['max'] != None:
                self.expiration_date=fields.Datetime.from_string(str(query_result['max'])).date()


        # for order in self:
        #     for line in order:
        #         multiplier_list = self.env['multiplier.multiplier'].search([('id', '=', line.multiplier.id)])
        #         line.margin = multiplier_list.margin
        #         line.offer_price = round(float(self.prod_qty) * float(line.price_unit) * (
        #                 float(multiplier_list.margin) / 100 + float(self.possible_competition.id) / 100),2)

        for order in self:
            for line in order:
                if (line.prod_qty == False):
                    line.prod_qty = '1'
                    line.product_retail = line.price_unit
                    line.product_unit_price = line.price_unit

        multiplier_list = self.env['multiplier.multiplier'].search([('id', '=', self.multiplier.id)])
        possible_competition_list = self.env['competition.competition'].search([('id', '=', self.possible_competition.id)])
        self.margin = multiplier_list.margin
        self.product_unit_price=math.ceil(round(float(self.price_unit) * (float(multiplier_list.retail) / 100),10))
        self.product_offer_price =math.ceil(round(float(self.product_unit_price) * (float(multiplier_list.margin) / 100 + float(possible_competition_list.margin) / 100),2))

    def expired_inventory_cal(self):
        expired_lot_count = 0
        test_id_list = self.env['stock.production.lot'].search([('product_id', '=', self.product_id.id)])
        for prod_lot in test_id_list:
            if prod_lot.use_date != False :
                if fields.Datetime.from_string(prod_lot.use_date).date() < fields.date.today():
                    expired_lot_count = expired_lot_count + 1

        self.expired_inventory = expired_lot_count

    @api.onchange('multiplier','prod_qty')
    def cal_offer_price(self):

        multiplier_list = self.env['multiplier.multiplier'].search([('id', '=', self.multiplier.id)])
        self.margin=multiplier_list.margin
        self.offer_price=round(float(self.prod_qty) * float(self.product_offer_price),2)
        self.product_retail = round(float(self.prod_qty) * float(self.product_unit_price),2)

    @api.multi
    def qty_in_stocks(self):
        domain = [
            ('product_id', '=',  self.product_id.id),
        ]
        moves = self.env['stock.move'].search(domain,limit=1)
        self.qty_in_stock=moves.product_qty

    # @api.onchange('prod_qty')
    # def prod_qty_onchange(self):
    #     print('------------------------------------------')
    #     self.product_retail=round(float(self.prod_qty)*float(self.price_unit),2)
    #     print(self.product_retail)


class Multiplier(models.Model):
    _name = 'multiplier.multiplier'
    _description = "Multiplier"

    name = fields.Char(string="Multiplier Name",required=True)
    code = fields.Char(string="Multiplier Code", required=True)
    retail = fields.Float('Retail %', digits=dp.get_precision('Product Unit of Measure'), required=True)
    margin = fields.Float('Margin %', digits=dp.get_precision('Product Unit of Measure'), required=True)


class Competition(models.Model):
    _name = 'competition.competition'
    _description = "Competition"

    name = fields.Char(string="Competition Name",required=True)
    margin = fields.Float('Margin %', digits=dp.get_precision('Product Unit of Measure'), required=True)


class Tier(models.Model):
    _name = 'tier.tier'
    _description = "Product Tier"

    name = fields.Char(string="Product Tier",required=True)
    code = fields.Char(string="Product Tier Code", required=True)


class ClassCode(models.Model):
    _name = 'classcode.classcode'
    _description = "Class Code"

    name=fields.Char(string="Class Code",required=True)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tier = fields.Many2one('tier.tier', string="Tier")
    class_code = fields.Many2one('classcode.classcode', string="Class Code")
