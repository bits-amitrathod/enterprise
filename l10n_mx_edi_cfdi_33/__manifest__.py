# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'EDI for Mexico with CFDI version 3.3',
    'version': '0.1',
    'category': 'Hidden',
    'summary': 'Mexican Localization for EDI documents CFDI version 3.3',
    'depends': ['l10n_mx_edi', 'base_address_city'],
    'external_dependencies': {
        'python': ['OpenSSL'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/3.3/cfdi.xml',
        'data/3.3/payment10.xml',
        'data/res_country_data.xml',
        'data/payment_method_data.xml',
        'views/account_view.xml',
        'views/account_invoice_view.xml',
        'views/account_report_payment_receipt_templates.xml',
        'views/account_payment_view.xml',
        'views/l10n_mx_edi_report_invoice.xml',
        'views/product_view.xml',
        'views/res_country_view.xml',
        'views/res_partner_view.xml',
    ],
    'demo': [
        'demo/config_parameter_demo.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': True,
}
