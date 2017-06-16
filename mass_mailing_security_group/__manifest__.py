# -*- coding: utf-8 -*-
# Copyright 2016 Tecnativa S.L. - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': "Mass mailing security group",
    'category': 'Marketing',
    'version': '10.0.1.0.0',
    'depends': [
        'mass_mailing',
        'marketing_campaign',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/mail_mass_mailing_security.xml',
    ],
    'author': 'Tecnativa, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.tecnativa.com',
    'license': 'AGPL-3',
    'installable': True,
}
