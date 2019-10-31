# Copyright 2019 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Mail Edit',
    'summary': """
        Allows you to edit chatter""",
    'version': '11.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Creu Blanca,Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/social',
    'depends': [
        'mail',
    ],
    'data': [
        'wizards/wizard_view_previous_editions.xml',
        'security/ir.model.access.csv',
        'views/mail_message.xml',
        'wizards/wizard_edit_message.xml',
        'views/assets_backend.xml',
    ],
    'qweb': [
        'static/src/xml/thread.xml',
    ],
}
