# -*- coding: utf-8 -*-
{
    'name': "Prioritization Engine",

    'summary': """
        Prioritization Engine""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Amit Rathod",
    'website': "http://www.benchmarkitsolutions.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '1.0',

    # any module necessary for this one to work correctly

<<<<<<< HEAD
    'depends': ['base','product','product_manufacturer','sale_management','stock','stock','web_one2many_selectable'],
=======
    'depends': ['base','product','product_manufacturer','sale_management','stock','web_one2many_selectable'],
>>>>>>> a0f42ba7747bb5d6218e74013a790d868f19cacf

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/saleorder_views.xml',
        'views/prioritization_views.xml',
        'views/web_assets.xml',
    ],

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'application': True,
    'auto-install': True,
    'installable': True,
}
