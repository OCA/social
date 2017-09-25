# -*- coding: utf-8 -*-
# © 2017 Phuc.nt - <phuc.nt@komit-consulting.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Mail split by partner",
    "version": "10.0.1.0.0",
    "author": "Komit, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Marketing",
    "website": "https://komit-consulting.com",
    'summary': "Split or merge recipients when send mail.",
    'depends': [
        'mail',
    ],
    'data': [
        'views/mail_mail_view.xml',
        'views/mail_template_view.xml',
        'data/ir_config_parameter.xml',
    ],
    'installable': True,
}
