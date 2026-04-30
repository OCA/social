{
    'name': 'Mail WhatsApp Chatter',
    'summary': 'Integrate WhatsApp messages into the Odoo mail chatter',
    'version': '16.0.1.0.0',
    'category': 'Discuss',
    'author': 'Madooit, Rodrigo A. Madureira',
    'website': 'https://madooit.com',
    'license': 'AGPL-3',
    'depends': ['mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_subtype.xml',
        'views/mail_message_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mail_whatsapp_chatter/static/src/scss/mail_whatsapp_chatter.scss',
            'mail_whatsapp_chatter/static/src/js/whatsapp_composer.js',
            # 'mail_whatsapp_chatter/static/src/xml/whatsapp_templates.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
