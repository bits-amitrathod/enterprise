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
        'website',
        'website_payment',
    ],
    'data': [
    ],
    'qweb': [
        'static/src/xml/*.xml'
    ],
    'demo': [
    ],
    'installable': True,
    'license': 'OEEL-1',
}
