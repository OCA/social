# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Mail Telegram',
    'summary': """
        Send messages to telegram""",
    'version': '11.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Creu Blanca',
    'website': 'https://github.com/OCA/social',
    'depends': [
        'mail',
    ],
    'data': [
        'data/mail_data.xml',
        'security/ir.model.access.csv',
        'views/mail_message_telegram.xml',
        'views/mail_telegram_chat.xml',
        'views/assets.xml',
    ],
    'qweb': [
        'static/src/xml/thread.xml',
    ],
}
