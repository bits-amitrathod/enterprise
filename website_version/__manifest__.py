{
    'name': 'Website Versioning',
    'category': 'Website',
    'summary': 'Create several website versions and perform A/B testing',
    'version': '1.0',
    'description': """
Never lose any data on your website when you are editing pages. With Website Versioning you can save any modification on your website pages and retrieve them through the versions.

You can save modifications as draft and publish it once it is ready.

The module also brings A/B testing in order to build the perfect website. Create several versions of your website pages.
Then run live experiments and find out which version perform best.
    """,
    'depends': ['website', 'mail', 'google_account'],
    'installable': True,
    'data': [
        'security/ir.model.access.csv',
        'views/website_version_templates.xml',
        'views/marketing_view.xml',
        'views/website_version_views.xml',
        'data/data.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'application': False,
    'license': 'OEEL-1',
}
