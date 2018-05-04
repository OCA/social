# -*- coding: utf-8 -*-
# Copyright © 2016 Savoir-faire Linux
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Mail Template Multi Report',
    'version': '10.0.1.0.0',
    'category': 'Marketing',
    'summary': 'Multiple Reports in Mail Templates',
    'author': 'Savoir-faire Linux, Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/social',
    'license': 'AGPL-3',
    'depends': [
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mail_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
