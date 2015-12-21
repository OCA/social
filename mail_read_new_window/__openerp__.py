# -*- coding: utf-8 -*-
# © 2015 initOS GmbH (<http://www.initos.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Mail open in new window',
    'summary': 'Open mail in new window',
    'version': '8.0.1.0.0',
    "category": "Social Network",
    'website': 'https://odoo-community.org',
    'author': 'initOS GmbH, Odoo Community Association (OCA)',
    "license": "AGPL-3",
    'application': False,
    'installable': True,
    'auto_install': False,
    'depends': [
        'mail',
        'web',
    ],
    'data': [
        'mail_read_new_window_view.xml',
    ],
    'qweb': [
        'static/src/xml/mail_read_new_window.xml',
    ],
}
