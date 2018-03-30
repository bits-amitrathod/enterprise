# -*- coding: utf-8 -*-
{
    'name': "web_dashboard",
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
Odoo Dashboard View.
========================

This module defines the Dashboard view, a new type of reporting view. This view
can embed graph and/or pivot views, and displays aggregate values.
        """,
    'depends': ['base'],
    'data': [
        'views/templates.xml',
    ],
    'qweb': [
        "static/src/xml/dashboard_view.xml",
    ],
    'auto_install': True,
}
