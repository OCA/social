# -*- coding: utf-8 -*-
# Copyright 2015-2018 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'SendGrid',
    'version': '10.0.1.0.2',
    'category': 'Social Network',
    'author': 'Compassion CH, Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'website': 'https://github.com/OCA/social',
    'depends': ['mail_tracking'],
    'data': [
        'security/ir.model.access.csv',
        'views/sendgrid_email_view.xml',
        'views/sendgrid_template_view.xml',
        'views/mail_compose_message_view.xml',
        'views/email_template_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'external_dependencies': {
        'python': ['sendgrid'],
    },
}
