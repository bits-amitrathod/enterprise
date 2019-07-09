# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from . import product

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _process_order(self, order):
        so = self.env['sale.order'].search(
            [('client_order_ref', '=', order['OrderID'])], limit=1)
        try:
            if not so:
                so = self._process_order_new(order)
            self._process_order_update(order, so)
        except Exception as e:
            message = _("Ebay could not synchronize order:\n%s") % str(e)
            path = str(order)
            product._log_logging(self.env, message, "_process_order", path)
            _logger.exception(message)

    @api.model
    def _process_order_new(self, order):
        (partner, shipping_partner) = self._process_order_new_find_partners(order)
        fp_id = self.env['account.fiscal.position'].get_fiscal_position(partner.id)
        if fp_id:
            partner.property_account_position_id = fp_id
        create_values = {
            'partner_id': partner.id,
            'partner_shipping_id': shipping_partner.id,
            'state': 'draft',
            'client_order_ref': order['OrderID'],
            'origin': 'eBay' + order['OrderID'],
            'fiscal_position_id': fp_id if fp_id else False,
        }
        if self.env['ir.config_parameter'].sudo().get_param('ebay_sales_team'):
            create_values['team_id'] = int(
                self.env['ir.config_parameter'].sudo().get_param('ebay_sales_team'))
        currency = self.env['res.currency'].search(
            [('name', '=', order['AmountPaid']['_currencyID'])], limit=1)
        create_values['currency_id'] = currency.id

        sale_order = self.env['sale.order'].create(create_values)

        for transaction in order['TransactionArray']['Transaction']:
            self._process_order_new_transaction(sale_order, transaction)

        self._process_order_shipping(order, sale_order)

        return sale_order

    @api.model
    def _process_order_new_find_partners(self, order):
        def _find_country():
            country = self.env['res.country'].search(
                [('code', '=', infos['Country'])], limit=1)
            return country
        def _find_state():
            state = self.env['res.country.state'].search([
                ('code', '=', infos.get('StateOrProvince')),
                ('country_id', '=', shipping_data['country_id'])
            ], limit=1)
            if not state:
                state = self.env['res.country.state'].search([
                    ('name', '=', infos.get('StateOrProvince')),
                    ('country_id', '=', shipping_data['country_id'])
                ], limit=1)
            return state
        def _set_email(partner_data):
            # After 15 days eBay doesn't send the email anymore but 'Invalid Request'.
            email = order['TransactionArray']['Transaction'][0]['Buyer']['Email']
            if email != 'Invalid Request':
                partner_data['email'] = email

        buyer_ebay_id = order['BuyerUserID']
        infos = order['ShippingAddress']

        partner = self.env['res.partner'].search([('ebay_id', '=', buyer_ebay_id)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({'name': buyer_ebay_id, 'ebay_id': buyer_ebay_id})
        partner_data = {
            'name': infos.get('Name'),
            'ebay_id': buyer_ebay_id,
            'ref': 'eBay',
        }
        _set_email(partner_data)
        # if we reuse an existing partner, addresses might already been set on it
        # so we hold the address data in a temporary dictionary to see if we need to create it or not
        shipping_data = {}
        info_to_extract = [('name', 'Name'), ('street', 'Street1'),
                           ('street2', 'Street2'), ('city', 'CityName'),
                           ('zip', 'PostalCode'), ('phone', 'Phone')]
        for (odoo_name, ebay_name) in info_to_extract:
            shipping_data[odoo_name] = infos.get(ebay_name, '')
        shipping_data['country_id'] = _find_country().id
        shipping_data['state_id'] = _find_state().id
        shipping_partner = partner._find_existing_address(shipping_data)
        if not shipping_partner:
            # if the partner already has an address we create a new child contact to hold it
            # otherwise we can directly set the new address on the partner
            if partner.street:
                contact_data = {'parent_id': partner.id, 'type': 'delivery'}
                shipping_partner = self.env['res.partner'].create({**shipping_data, **contact_data})
            else:
                partner.write(shipping_data)
                shipping_partner = partner
        partner.write(partner_data)

        return (partner, shipping_partner)

    @api.model
    def _handle_taxes(self, amount, rate):
        company = self.env.user.company_id
        tax = False
        if amount > 0 and rate > 0:
            tax = self.env['account.tax'].sudo().search([
                ('amount', '=', rate),
                ('amount_type', '=', 'percent'),
                ('company_id', '=', company.id),
                ('type_tax_use', '=', 'sale')], limit=1)
            if not tax:
                tax = self.env['account.tax'].sudo().create({
                    'name': 'Tax %.3f %%' % rate,
                    'amount': rate,
                    'amount_type': 'percent',
                    'type_tax_use': 'sale',
                    'description': 'Sales Tax (eBay)',
                    'company_id': company.id,
                })
        return tax

    @api.model
    def _find_currency(self, name=''):
        domain = [('name', '=', name)]
        return self.env['res.currency'].search(domain, limit=1)

    @api.model
    def _process_order_shipping(self, order, sale_order):
        if 'ShippingServiceSelected' in order:
            shipping_cost_dict = order['ShippingServiceSelected']['ShippingServiceCost']
            shipping_amount = float(shipping_cost_dict['value'])
            shipping_currency = self._find_currency(shipping_cost_dict['_currencyID'])
            shipping_name = order['ShippingServiceSelected']['ShippingService']
            shipping_product = self.env['product.template'].search(
                [('name', '=', shipping_name)], limit=1)
            if not shipping_product:
                shipping_product = self.env['product.template'].create({
                    'name': shipping_name,
                    'type': 'service',
                    'categ_id': self.env.ref('sale_ebay.product_category_ebay').id,
                })
            tax_dict = order['ShippingDetails']['SalesTax']
            tax_amount = float(tax_dict.get('SalesTaxAmount', {}).get('value', 0))
            tax_rate = float(tax_dict.get('SalesTaxPercent', 0))
            tax_id = self._handle_taxes(tax_amount, tax_rate)

            price_unit = shipping_currency._convert(shipping_amount - tax_amount,
                sale_order.currency_id, self.env.user.company_id, datetime.now())

            so_line = self.env['sale.order.line'].create({
                'order_id': sale_order.id,
                'name': shipping_name,
                'product_id': shipping_product.product_variant_ids[0].id,
                'product_uom_qty': 1,
                'price_unit': price_unit,
                'tax_id': [(4, tax_id.id)] if tax_id else False,
                'is_delivery': True,
            })

    @api.model
    def _process_transaction_product(self, transaction):
        Template = self.env['product.template']
        ebay_id = transaction['Item']['ItemID']
        product = Template.search([('ebay_id', '=', ebay_id)], limit=1)
        if not product:
            product = Template.create({
                'name': transaction['Item']['Title'],
                'ebay_id': ebay_id,
                'ebay_use': True,
                'ebay_sync_stock': False,
            })
            product.message_post(body=
                _('Product created from eBay transaction %s') % transaction['TransactionID'])

        if product.product_variant_count > 1:
            if 'Variation' in transaction:
                variant = product.product_variant_ids.filtered(
                    lambda l:
                    l.ebay_use and
                    l.ebay_variant_url.split("vti", 1)[1] ==
                    transaction['Variation']['VariationViewItemURL'].split("vti", 1)[1])
            # If multiple variants but only one listed on eBay as Item Specific
            else:
                call_data = {'ItemID': product.ebay_id, 'IncludeItemSpecifics': True}
                resp = product.ebay_execute('GetItem', call_data)
                name_value_list = resp.dict()['Item']['ItemSpecifics']['NameValueList']
                if not isinstance(name_value_list, list):
                    name_value_list = [name_value_list]
                # get only the item specific in the value list
                attrs = []
                # get the attribute.value ids in order to get the variant listed on ebay
                for spec in (n for n in name_value_list if n['Source'] == 'ItemSpecific'):
                    attr = product.env['product.attribute.value'].search(
                        [('name', '=', spec['Value'])])
                    attrs.append(('attribute_value_ids', '=', attr.id))
                variant = product.env['product.product'].search(attrs).filtered(
                    lambda l: l.product_tmpl_id.id == product.id)
        else:
            variant = product.product_variant_ids[0]
        variant.ebay_quantity_sold = variant.ebay_quantity_sold + int(transaction['QuantityPurchased'])
        if not product.ebay_sync_stock:
            variant.ebay_quantity = variant.ebay_quantity - int(transaction['QuantityPurchased'])
            variant_qty = 0
            if len(product.product_variant_ids.filtered('ebay_use')) > 1:
                for variant in product.product_variant_ids:
                    variant_qty += variant.ebay_quantity
            else:
                variant_qty = variant.ebay_quantity
            if variant_qty <= 0:
                if self.env['ir.config_parameter'].sudo().get_param('ebay_out_of_stock'):
                    product.ebay_listing_status = 'Out Of Stock'
                else:
                    product.ebay_listing_status = 'Ended'
        return product, variant

    @api.model
    def _process_order_new_transaction(self, sale_order, transaction):
        product, variant = self._process_transaction_product(transaction)

        transaction_currency = self._find_currency(
            transaction['TransactionPrice']['_currencyID'])
        price_unit = float(transaction['TransactionPrice']['value'])
        tax_amount = float(transaction['Taxes']['TotalTaxAmount']['value'])
        tax_rate = tax_amount / price_unit if price_unit > 0 else 0
        tax_id = self._handle_taxes(tax_amount, tax_rate)
        price_unit = transaction_currency._convert(price_unit,
            sale_order.currency_id, self.env.user.company_id, datetime.now())

        sol = self.env['sale.order.line'].create({
            'product_id': variant.id,
            'order_id': sale_order.id,
            'name': variant.name,
            'product_uom_qty': float(transaction['QuantityPurchased']),
            'product_uom': variant.uom_id.id,
            'price_unit': price_unit,
            'tax_id': [(4, tax_id.id)] if tax_id else False,
        })

        if 'BuyerCheckoutMessage' in transaction:
            sale_order.message_post(body=_('The Buyer Posted :\n') + transaction['BuyerCheckoutMessage'])

        self.env['product.template']._put_in_queue(product.id)

    @api.model
    def _process_order_update(self, order, sale_order):
        sale_order.ensure_one()

        product_lines = sale_order.order_line.filtered(lambda l: not l._is_delivery())
        are_all_products_listed = all(product_lines.mapped('product_id.ebay_url'))
        can_be_invoiced = ('order' in product_lines.mapped('product_id.invoice_policy') and
                           'to invoice' in product_lines.mapped('invoice_status'))

        no_confirm = (self.env.context.get('ebay_no_confirm', False) or
                      not are_all_products_listed)
        try:
            if (not no_confirm and sale_order.state in ['draft', 'sent']):
                sale_order.action_confirm()
            if not no_confirm and can_be_invoiced:
                sale_order.action_invoice_create()
            shipping_name = order['ShippingServiceSelected']['ShippingService']
            if sale_order.picking_ids and shipping_name:
                sale_order.picking_ids.message_post(
                    body=_('The Buyer Chose The Following Delivery Method :\n') + shipping_name)
        except UserError as e:
            sale_order.message_post(body=
                _('Ebay Synchronisation could not confirm because of the following error:\n%s') % str(e))
