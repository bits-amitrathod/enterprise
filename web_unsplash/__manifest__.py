# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Web Unsplash',
    'category': 'Web',
    'summary': 'Allow to use unsplash images in website.',
    'version': '1.0',
    'description': """Allow to use unsplash images in website.""",
    'depends': ['web_editor'],
    'data': [
        'views/res_config_settings_view.xml',
        'views/web_unsplash_templates.xml',
    ],
}
