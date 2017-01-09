# -*- coding: utf-8 -*-
from odoo.tests import common


class TestSubscriptionCommon(common.TransactionCase):

    def setUp(self):
        super(TestSubscriptionCommon, self).setUp()

        self.env.user.company_id.currency_id = self.env.ref('base.EUR')

        Subscription = self.env['sale.subscription']
        Template = self.env['sale.subscription.template']
        Product = self.env['product.product']
        UomCat = self.env['product.uom.categ']
        Uom = self.env['product.uom']
        # Analytic Account
        self.master_tag = self.env['account.analytic.tag'].create({
            'name': 'Test Tag',
        })

        # Units of measure
        self.uom_cat = UomCat.create({
            'name': 'Test Cat',
        })
        self.uom_base = Uom.create({
            'name': 'Base uom',
            'category_id': self.uom_cat.id,
        })
        self.uom_big = Uom.create({
            'name': '10x uom',
            'category_id': self.uom_cat.id,
            'uom_type': 'bigger',
            'factor_inv': 10,
        })

        # Test Subscription Template
        self.subscription_tmpl_1 = Template.create({
            'name': 'TestSubscriptionTemplate1',
            'recurring_rule_type': 'yearly',
            'tag_id': self.master_tag.id,
        })
        self.subscription_tmpl_2 = Template.create({
            'name': 'TestSubscriptionTemplate2',
            'recurring_rule_type': 'monthly',
            'tag_id': self.master_tag.id,
        })

        # Test products
        self.product = Product.create({
            'name': 'TestProduct',
            'type': 'service',
            'recurring_invoice': True,
            'subscription_template_id': self.subscription_tmpl_1.id,
            'uom_id': self.uom_big.id,
            'uom_po_id': self.uom_big.id,
            'price': 500.0
        })
        self.product2 = Product.create({
            'name': 'TestProduct2',
            'type': 'service',
            'recurring_invoice': True,
            'subscription_template_id': self.subscription_tmpl_2.id,
            'uom_id': self.uom_base.id,
            'uom_po_id': self.uom_base.id,
            'price': 15.0
        })
        self.product3 = Product.create({
            'name': 'TestProduct3',
            'type': 'service',
            'recurring_invoice': True,
            'subscription_template_id': self.subscription_tmpl_2.id,
            'uom_id': self.uom_base.id,
            'uom_po_id': self.uom_base.id,
            'price': 20.0
        })

        self.subscription_tmpl_1.write({
            'subscription_template_option_ids': [(0, 0, {'product_id': self.product2.id, 'name': 'TestRecurringLine', 'uom_id': self.product2.uom_id.id})]
        })
        self.subscription_tmpl_2.write({
            'subscription_template_option_ids': [(0, 0, {'product_id': self.product.id, 'name': 'TestRecurringLine', 'uom_id': self.product.uom_id.id})]
        })

        # Test user
        TestUsersEnv = self.env['res.users'].with_context({'no_reset_password': True})
        group_portal_id = self.ref('base.group_portal')
        self.user_portal = TestUsersEnv.create({
            'name': 'Beatrice Portal',
            'login': 'Beatrice',
            'email': 'beatrice.employee@example.com',
            'groups_id': [(6, 0, [group_portal_id])]
        })

        # Test Subscription
        self.subscription = Subscription.create({
            'name': 'TestSubscription',
            'recurring_rule_type': 'yearly',
            'pricelist_id': self.ref('product.list0'),
            'state': 'open',
            'partner_id': self.user_portal.partner_id.id,
            'template_id': self.subscription_tmpl_1.id,
            'recurring_invoice_line_ids': [(0, 0, {'product_id': self.product.id, 'name': 'TestRecurringLine', 'price_unit': self.product.list_price, 'uom_id': self.product.uom_id.id})],
        })
