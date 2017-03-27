# -*- coding: utf-8 -*-

{
    'name': 'Subscription Upsells',
    'summary': 'Pro-rated options on subscriptions',
    'description': """
""",
    'depends': ['website_subscription', 'website_sale'],
    'data': [
        'views/sale_subscription_views.xml',
        'views/sale_subscription_templates.xml',
    ],
    'demo': [
        'data/website_subscription_upsell_demo.xml',
    ],
}
