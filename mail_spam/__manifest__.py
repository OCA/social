# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    'name': 'Anti-Spam',
    'summary': 'Provides anti-SPAM support powered by Pyzor.',
    'version': '10.0.1.0.0',
    'category': 'Mail',
    'website': 'https://laslabs.com/',
    'author': 'LasLabs, Odoo Community Association (OCA)',
    'license': 'LGPL-3',
    'application': False,
    'installable': True,
    'post_init_hook': 'post_init_hook',
    'external_dependencies': {
        'python': ['pyzor'],
    },
    'depends': [
        'mail',
    ],
    'data': [
        'data/reverend_thomas_data.xml',
        'templates/assets.xml',
        'views/res_company_view.xml',
    ],
    'qweb': [
        'static/src/xml/mail_message_template.xml',
    ],
}
