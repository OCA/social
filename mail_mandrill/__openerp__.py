# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Antonio Espinosa
# See README.rst file on addon root folder for more details

{
    'name': "Mandrill mail events integration",
    'category': 'Social Network',
    'version': '8.0.1.0.0',
    'depends': [
        'mail',
    ],
    'external_dependencies': {},
    'data': [
        'security/ir.model.access.csv',
        'views/mail_mandrill_message_view.xml',
        'views/mail_mandrill_event_view.xml',
    ],
    'author': 'Antiun Ingeniería S.L., '
              'Odoo Community Association (OCA)',
    'website': 'http://www.antiun.com',
    'license': 'AGPL-3',
    'demo': [],
    'test': [],
    'installable': True,
}
