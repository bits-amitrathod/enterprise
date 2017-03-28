# -*- coding: utf-8 -*-
import calendar
import datetime

from .test_common import TestSubscriptionCommon
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger, float_utils


class TestSubscription(TestSubscriptionCommon):

    def test_templates(self):
        """ Test subscription templates error when introducing duplicate option lines """

        with self.assertRaises(ValidationError):
            self.subscription_tmpl_1.write({
                'subscription_template_option_ids': [(0, 0, {'product_id': self.product_opt.id, 'name': 'TestRecurringLine', 'uom_id': self.uom_base.id})]
            })

    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
    def test_subscription(self):
        """ Test behaviour of subscription change """
        # switch plan: check that mandatory lines have been modified accordingly
        self.subscription.change_subscription(self.subscription_tmpl_2.id)
        self.assertEqual(self.subscription.template_id.id, self.subscription_tmpl_2.id, 'website_subscription: template not changed when changing subscription from the frontend')
        self.assertEqual(len(self.subscription.recurring_invoice_line_ids), 2, 'website_subscription: number of lines after switching plan does not match mandatory lines of new plan')
        self.assertEqual(self.subscription.recurring_total, 650, 'website_subscription: price after switching plan is wrong')

        # add option
        self.subscription.add_option(self.subscription_tmpl_2.subscription_template_option_ids.id)
        self.assertEqual(len(self.subscription.recurring_invoice_line_ids), 3, 'website_subscription: number of lines after adding option does not add up')
        self.assertEqual(self.subscription.recurring_total, 850, 'website_subscription: recurring price after adding option is wrong')

        # switch back: option should be preserved, other lines should have been changed
        self.subscription.change_subscription(self.subscription_tmpl_1.id)
        self.assertEqual(len(self.subscription.recurring_invoice_line_ids), 2, 'website_subscription: number of lines after switching plan twice does add up')
        self.assertEqual(self.subscription.recurring_total, 70, 'website_subscription: recurring price after switching plan twice is wrong')

    def test_upsell(self):
        self.sale_order = self.env['sale.order'].create({
            'name': 'TestSO',
            'project_id': self.subscription.analytic_account_id.id,
            'subscription_id': self.subscription.id,
            'partner_id': self.user_portal.partner_id.id,
        })
        current_year = int(datetime.datetime.strftime(datetime.date.today(), '%Y'))
        current_day = datetime.datetime.now().timetuple().tm_yday
        self.subscription.recurring_next_date = '%s-01-01' % (current_year + 1)
        is_leap = calendar.isleap(current_year)
        fraction = float(current_day) / (365.0 if not is_leap else 366.0)
        self.subscription.partial_invoice_line(self.sale_order, self.subscription_tmpl_1.subscription_template_option_ids)
        invoicing_ratio = self.sale_order.order_line.discount / 100.0
        # discount should be equal to prorata as computed here
        self.assertEqual(float_utils.float_compare(fraction, invoicing_ratio, precision_digits=2), 0, 'website_subscription: partial invoicing ratio calculation mismatch')
        self.sale_order.action_confirm()
        self.assertEqual(len(self.subscription.recurring_invoice_line_ids), 2, 'website_subscription: number of lines after adding pro-rated discounted option does not add up')
        # there should be no discount on the subscription line in this case
        self.assertEqual(self.subscription.recurring_total, 70, 'website_subscription: price after adding pro-rated discounted option does not add up')

    def test_sub_creation(self):
        order = self.env['sale.order'].create({
            'name': 'TestSOTemplate',
            'partner_id': self.user_portal.partner_id.id,
            'template_id': self.quote_template.id,
        })

        order.onchange_template_id()
        order.action_confirm()
        self.assertTrue(order.subscription_id, 'website_subscription: subscription is not created at so confirmation')
        self.assertEqual(order.subscription_management, 'create', 'website_subscription: subscription creation should set the so to "create"')

    def test_recurring_revenue(self):
        """Test computation of recurring revenue"""
        eq = lambda x, y, m: self.assertAlmostEqual(x, y, msg=m)
        # Initial subscription is $50/y
        y_price = 50
        eq(self.subscription.recurring_total, y_price, "unexpected price after setup")
        eq(self.subscription.recurring_monthly, y_price / 12.0, "unexpected MRR")
        # Switch to $650/month
        m_price = 650
        self.subscription.change_subscription(self.subscription_tmpl_2.id)
        eq(self.subscription.recurring_total, m_price, 'unexpected recurring total')
        eq(self.subscription.recurring_monthly, m_price, 'unexpected MRR')
        # Change interval to 3 weeks
        self.subscription.template_id.recurring_rule_type = 'weekly'
        self.subscription.template_id.recurring_interval = 3
        eq(self.subscription.recurring_total, m_price, 'total should not change when interval changes')
        eq(self.subscription.recurring_monthly, m_price * (30 / 7.0) / 3, 'unexpected MRR')
