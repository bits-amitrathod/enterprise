{
    'name': 'Online Subscriptions',
    'category': 'Website',
    'sequence': 32,
    'summary': 'Subscriptions Management Frontend for your customers',
    'version': '1.0',
    'description': """
This module allows your customers to manage their subscriptions.

Features:
    - Generate invoice and credit card payments automatically at fixed intervals
    - Let your customer edit their subscriptions themselves (close their subscription, communicate through the chatter) with granular control
        """,
    'depends': [
        'sale_subscription',
        'website_sale',
        'website_portal',
        'website_quote',
        'website_payment',
        'sale_subscription_dashboard',
    ],
    'data': [
        'views/sale_subscription_templates.xml',
        'views/sale_subscription_views.xml',
        'views/payment_acquirer_views.xml',
        'security/ir.model.access.csv',
        'security/portal_subscription_security.xml',
        'data/data.xml'
    ],
    'qweb': [
        'static/src/xml/*.xml'
    ],
    'demo': [
        #if any, demo data should be created using yml files, in the same flavour then in account_asset
        'data/demo.xml',
        'data/demo.yml',
    ],
    'installable': True,
    'application': True,
    'license': 'OEEL-1',
}
