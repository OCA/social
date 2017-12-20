# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    'name': 'Mail Anti-SPAM',
    'summary': 'Provides SPAM filtering using Bayesian classification.',
    'version': '10.0.1.0.0',
    'category': 'Mail',
    'website': 'https://laslabs.com/',
    'author': 'LasLabs, Odoo Community Association (OCA)',
    'license': 'LGPL-3',
    'application': False,
    'installable': True,
    'post_init_hook': 'post_init_hook',
    'external_dependencies': {
        'python': ['reverend'],
    },
    'depends': [
        'mail',
    ],
    'data': [
        'data/reverend_thomas_data.xml',
        'templates/assets.xml',
        'views/res_company_view.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': [
        'static/src/xml/mail_message_template.xml',
    ],
}
