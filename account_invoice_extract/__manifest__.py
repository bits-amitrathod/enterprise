# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Account Invoice Extract',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Extract data from invoice scans',
    'depends': ['account', 'iap', 'mail_enterprise', 'l10n_generic_coa'],
    'demo': [
        'demo/account_in_invoice_demo.xml',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/extraction_status.xml',
        'data/res_config_settings_views.xml',
    ],
}
