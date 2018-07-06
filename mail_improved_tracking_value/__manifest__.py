# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Improved tracking value change',
    'version': '10.0.1.0.0',
    'summary': 'Improves tracking changed values for certain type of fields.'
               'Adds a user-friendly view to consult them.',
    'author': 'Camptocamp, Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'category': 'Tools',
    'website': 'http://www.camptocamp.com',
    'depends': [
        'base',
        'mail'
    ],
    'data': [
        'views/mail_tracking_value.xml'
    ],
    'installable': True,
    'auto_install': False,
}
