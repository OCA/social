# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Mail Telegram Broker',
    'summary': """
        Set a broker for telegram""",
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Creu Blanca,Odoo Community Association (OCA)',
    'website': 'www.creublanca.es',
    'depends': [
        'mail_telegram',
    ],
    'qweb': ['static/src/xml/broker.xml'],
    'pre_init_hook': 'pre_init_hook',
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/mail_telegram_bot.xml',
        'templates/assets.xml',
        'views/mail_telegram_chat.xml',
    ],
}
