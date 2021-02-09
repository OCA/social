# -*- coding: utf-8 -*-
# Copyright 2016-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Mass Mailing with SendGrid',
    'version': '10.0.1.0.1',
    'category': 'Social Network',
    'author': 'Compassion CH, Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'website': 'https://github.com/OCA/social',
    'depends': ['mail_sendgrid', 'mail_tracking_mass_mailing'],
    'data': [
        'views/mass_mailing_view.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
    'external_dependencies': {
        'python': ['sendgrid'],
    },
}
