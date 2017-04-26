# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SMS FortyTwo Provider',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 40,
    'summary': 'FortyTwo SMS Gateway',
    'description': """
    Send SMS text messages with FortyTwo SMS Services.
""",
    'depends': ['sms'],
    'data': [
        'views/sms_views.xml',
    ],
    'application': False,
    'auto_install': True, # True while no other provider is implemented
}
