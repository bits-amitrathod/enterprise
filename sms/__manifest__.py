# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SMS base',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 40,
    'summary': 'SMS Text Messaging',
    'description': """
This module gives a framework for SMS text messaging
----------------------------------------------------

You need to install a provider alongside of this module in order to be able send SMS text messages.
""",
    'depends': ['base', 'mail'],
    'data': [
        'views/sms_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/sms_message_send_views.xml',
        'security/ir.model.access.csv',
    ],
    'application': False,
    'auto_install': False,
}
