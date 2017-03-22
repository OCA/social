# -*- coding: utf-8 -*-
# Copyright 2017 Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': 'Mail digest',
    'summary': """Basic digest mail handling.""",
    'version': '9.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Camptocamp,Odoo Community Association (OCA)',
    'depends': [
        'mail',
    ],
    'data': [
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'views/mail_digest_views.xml',
        'views/partner_views.xml',
        'views/user_views.xml',
        'templates/digest_default.xml',
    ],
}
