# -*- coding: utf-8 -*-
# © 2016 Savoir-faire Linux
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Email Template Multi Report',
    'version': '8.0.1.0.0',
    'category': 'Marketing',
    'summary': 'Multiple Reports in Email Templates',
    'author': 'Savoir-faire Linux,Odoo Community Association (OCA)',
    'website': 'http://www.savoirfairelinux.com',
    'license': 'AGPL-3',
    'depends': [
        'email_template',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/email_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
