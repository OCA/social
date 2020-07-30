# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Mail Telegram',
    'summary': """
        Send messages to telegram""",
    'version': '12.0.1.0.1',
    'license': 'AGPL-3',
    'author': 'Creu Blanca,Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/social',
    'depends': [
        'mail',
    ],
    'data': [
        'data/mail_data.xml',
        'security/ir.model.access.csv',
        'views/mail_message_telegram.xml',
        'views/mail_telegram_chat.xml',
        'views/mail_telegram_bot.xml',
        'views/assets.xml',
    ],
    'external_dependencies': {
        'python': ['telegram'],
    },
    'qweb': [
        'static/src/xml/thread.xml',
    ],
}
