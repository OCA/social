# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Javier Iniesta
# See README.rst file on addon root folder for more details

{
    'name': "Mass mailing from events",
    'category': 'Marketing',
    'version': '8.0.1.0.0',
    'depends': [
        'event',
        'mass_mailing'
    ],
    'data': [
        'views/event_registration.xml',
        'wizard/event_registration_mail_list_wizard.xml',
    ],
    'author': 'Antiun Ingeniería S.L.,Odoo Community Association (OCA)',
    'website': 'http://www.antiun.com',
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': True,
}
