{
    'name': 'Website Sale Dashboard With Margin',
    'category': 'Technical Settings',
    'sequence': 55,
    'summary': 'Get margin information in your e-commerce dashboard',
    'version': '1.0',
    'description': """
This module adds the average margin of your online sales to the statistics displayed in the Website application new dashboard view.
    """,
    'depends': ['website_sale', 'web_dashboard', 'sale_margin'],
    'data': [
        'views/dashboard_view.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': True,
}
