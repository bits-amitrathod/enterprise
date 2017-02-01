# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'EDI for Mexico',
    'version': '0.1',
    'category': 'Hidden',
    'summary': 'Mexican Localization for EDI documents',
    'description': """
EDI Mexican Localization
========================
Allow the user to generate the EDI document for Mexican invoicing.

This module allows the creation of the EDI documents and the communication with the Mexican certification providers (PACs) to sign/cancel them.
    """,
    'depends': ['account', 'base_vat', 'base_address_extended'],
    'data': [
        'security/ir.model.access.csv',
        'data/3.2/cfdv32.xml',
        'data/account_data.xml',
        'data/payment_method_data.xml',
        'views/account_invoice_view.xml',
        'views/res_config_view.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/ir_ui_view_view.xml',
        'views/certificate_view.xml',
        "views/payment_method_view.xml",
        'views/account_view.xml',
        "views/l10n_mx_edi_report_invoice.xml",
    ],
    'demo': [
        'demo/ir_ui_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
