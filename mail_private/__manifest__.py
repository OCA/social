# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Mail Private',
    'summary': """
        Create private emails""",
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Creu Blanca,Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/social',
    'depends': [
        'mail',
    ],
    'qweb': [
        'static/src/xml/thread.xml',
        'static/src/xml/composer.xml',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mail_security_group.xml',
        'wizards/mail_compose_message.xml',
        'security/security.xml',
        'views/ir_model.xml',
        'views/assets.xml',
        'views/mail_message.xml',
    ],
}
