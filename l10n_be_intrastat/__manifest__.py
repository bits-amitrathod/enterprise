# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgian Intrastat Declaration',
    'category': 'Localization',
    'description': """
Generates Intrastat XML report for declaration
Based on invoices.
    """,
    'depends': ['l10n_be', 'account_intrastat'],
    'data': [
        'data/code_region_data.xml',
        'data/intrastat_export.xml',
        'views/res_users_views.xml',
    ],
    'auto_install': True,
}
