# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sign',
    'version': '1.0',
    'category': 'Document Management',
    'summary': "Send documents to sign online, receive and archive filled copies (esign)",
    'description': """
Sign and complete your documents easily. Customize your documents with text and signature fields and send them to your recipients.\n
Let your customers follow the signature process easily.
    """,
    'website': 'http://www.odoo.com',
    'depends': ['mail', 'document', 'portal'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'views/sign_request_templates.xml',
        'views/sign_template_templates.xml',

        'views/sign_request_views.xml',
        'views/sign_template_views.xml',

        'views/res_users_views.xml',
        'views/res_partner_views.xml',

        'data/sign_data.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'demo': [
        'data/sign_demo.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'OEEL-1',
}
