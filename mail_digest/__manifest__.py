# Copyright 2017-2018 Camptocamp - Simone Orsi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': 'Mail digest',
    'summary': """Basic digest mail handling.""",
    'version': '11.0.1.0.1',
    'license': 'AGPL-3',
    'author': 'Camptocamp, Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/social',
    'depends': [
        'mail',
    ],
    'data': [
        'data/ir_cron.xml',
        'data/config_param.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'views/mail_digest_views.xml',
        'views/user_notification_views.xml',
        'views/user_views.xml',
        'templates/digest_default.xml',
    ],
    'images': [
        'static/description/preview.png',
    ]
}
