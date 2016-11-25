# -*- coding: utf-8 -*-
# © 2016 Tecnativa S.L. - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': "Mass mailing security group",
    'category': 'Marketing',
    'version': '9.0.1.0.0',
    'depends': [
        'mass_mailing',
    ],
    'external_dependencies': {},
    'data': [
        'security/ir.model.access.csv',
        'security/mail_mass_mailing_security.xml',
    ],
    'author': 'Tecnativa, '
              'Odoo Community Association (OCA)',
    'website': 'http://www.tecnativa.com',
    'license': 'AGPL-3',
    'installable': True,
}
