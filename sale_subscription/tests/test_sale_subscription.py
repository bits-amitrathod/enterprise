# -*- coding: utf-8 -*-
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.tools import mute_logger


class TestSubscription(TestSubscriptionCommon):

    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
    def test_template(self):
        """ Test behaviour of on_change_template """
        Subscription = self.env['sale.subscription']

        # on_change_template on existing record (present in the db)
        self.subscription.template_id = self.subscription_tmpl
        self.subscription.on_change_template()
        self.assertTrue(len(self.subscription.recurring_invoice_line_ids.ids) == 0, 'sale_subscription: recurring_invoice_line_ids copied on existing sale.subscription record')

        # on_change_template on cached record (NOT present in the db)
        temp = Subscription.new({'name': 'CachedSubscription',
                             'type': 'subscription',
                             'state': 'open',
                             'partner_id': self.user_portal.partner_id.id
                             })
        temp.update({'template_id': self.subscription_tmpl.id})
        temp.on_change_template()
        self.assertTrue(temp.mapped('recurring_invoice_line_ids').mapped('name'), 'sale_subscription: recurring_invoice_line_ids not copied on new cached sale.subscription record')

    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
    def test_sale_order(self):
        """ Test sales order line copying for recurring products on confirm"""
        self.sale_order.action_confirm()
        self.assertTrue(len(self.subscription.recurring_invoice_line_ids.ids) == 1, 'sale_subscription: recurring_invoice_line_ids not created when confirming sale_order with recurring_product')
        self.assertEqual(self.sale_order.state, 'done', 'sale_subscription: so state should be after confirmation done when there is a subscription')
        self.assertEqual(self.sale_order.subscription_management, 'upsell', 'sale_subscription: so should be set to "upsell" if not specified otherwise')

    def test_sub_creation(self):
        """ Test multiple subscription creation from single SO"""
        # Test subscription creation on SO confirm
        self.sale_order_2.action_confirm()
        self.assertEqual(len(self.sale_order_2.order_line.mapped('subscription_id')), 1, 'sale_subscription: subscription should be created on SO confirmation')
        self.assertEqual(self.sale_order_2.subscription_management, 'create', 'sale_subscription: subscription creation should set the SO to "create"')

        # Two product with different subscription template
        self.sale_order_3.action_confirm()
        self.assertEqual(len(self.sale_order_3.order_line.mapped('subscription_id')), 2, 'sale_subscription: Two different subscription should be created on SO confirmation')
        self.assertEqual(self.sale_order_3.subscription_management, 'create', 'sale_subscription: subscription creation should set the SO to "create"')

        # Two product with same subscription template
        self.sale_order_4.action_confirm()
        self.assertEqual(len(self.sale_order_4.order_line.mapped('subscription_id')), 1, 'sale_subscription: One subscription should be created on SO confirmation')
        self.assertEqual(self.sale_order_4.subscription_management, 'create', 'sale_subscription: subscription creation should set the SO to "create"')

    def test_renewal(self):
        """ Test subscription renewal """
        res = self.subscription.prepare_renewal_order()
        renewal_so_id = res['res_id']
        renewal_so = self.env['sale.order'].browse(renewal_so_id)
        self.assertTrue(renewal_so.subscription_management == 'renew', 'sale_subscription: renewal quotation generation is wrong')
        self.subscription.write({'recurring_invoice_line_ids': [(0, 0, {'product_id': self.product.id, 'name': 'TestRecurringLine', 'price_unit': 50, 'uom_id': self.product.uom_id.id})]})
        renewal_so.write({'order_line': [(0, 0, {'product_id': self.product.id, 'subscription_id': self.subscription.id, 'name': 'TestRenewalLine', 'product_uom': self.product.uom_id.id})]})
        renewal_so.action_confirm()
        lines = [line.name for line in self.subscription.mapped('recurring_invoice_line_ids')]
        self.assertTrue('TestRecurringLine' not in lines, 'sale_subscription: old line still present after renewal quotation confirmation')
        self.assertTrue('TestRenewalLine' in lines, 'sale_subscription: new line not present after renewal quotation confirmation')
        self.assertEqual(renewal_so.state, 'done', 'sale_subscription: so state should be after confirmation done when there is a subscription')
        self.assertEqual(renewal_so.subscription_management, 'renew', 'sale_subscription: so should be set to "renew" in the renewal process')
