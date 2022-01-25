{
    'name': "Mail Push Notifications",
    'summary': """Add push notifications for incoming messages""",
    'version': '12.0.1.0.1',
    'author': "BADEP, Odoo Community Association (OCA)",
    'website': 'https://github.com/OCA/social',
    'license': 'AGPL-3',
    'category': 'Discuss',
    'depends': ['mail', 'web'],
    'external_dependencies': {
        'python': [
            'pyfcm',
            'html2text',
        ],
    },
    'images': ['static/scr/img/banner.png'],
    'data': [
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'security/mail_notify_security.xml',
        'views/assets.xml',
        'views/res_config_settings_views.xml'
    ],
}
