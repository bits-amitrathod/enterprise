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
                'subscription_template_option_ids': [(0, 0, {'product_id': self.product2.id, 'name': 'TestRecurringLine', 'uom_id': self.product2.uom_id.id})]
            })

    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
    def test_subscription(self):
        """ Test behaviour of subscription options """
        # add option
        self.subscription.add_option(self.subscription_tmpl_1.subscription_template_option_ids.id)
        self.assertEqual(len(self.subscription.recurring_invoice_line_ids), 2, 'website_subscription: number of lines after adding option does not add up')
        self.assertEqual(self.subscription.recurring_total, 519.25, 'website_subscription: recurring price after adding option is wrong')

        # remove option
        self.subscription.remove_option(self.subscription_tmpl_1.subscription_template_option_ids.id)
        self.assertEqual(len(self.subscription.recurring_invoice_line_ids), 1, 'website_subscription: number of lines after removing option does not remove')
        self.assertEqual(self.subscription.recurring_total, 500, 'website_subscription: recurring price after removing option is wrong')

    def test_upsell(self):
        self.sale_order = self.env['sale.order'].create({
            'name': 'TestSO',
            'project_id': self.subscription.analytic_account_id.id,
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
        self.assertEqual(self.subscription.recurring_total, 519.25, 'website_subscription: price after adding pro-rated discounted option does not add up')

    def test_recurring_revenue(self):
        """Test computation of recurring revenue"""
        eq = lambda x, y, m: self.assertAlmostEqual(x, y, msg=m)
        # Initial subscription is $500/y
        y_price = 500
        eq(self.subscription.recurring_total, y_price, "unexpected price after setup")
        eq(self.subscription.recurring_monthly, y_price / 12.0, "unexpected MRR")
        # Change interval to 3 weeks
        self.subscription.template_id.recurring_rule_type = 'weekly'
        self.subscription.template_id.recurring_interval = 3
        eq(self.subscription.recurring_total, y_price, 'total should not change when interval changes')
        eq(self.subscription.recurring_monthly, y_price * (30 / 7.0) / 3, 'unexpected MRR')
