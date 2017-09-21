# -*- coding: utf-8 -*-
# © 2017 Phuc.nt
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Mail split by partner",
    "version": "10.0.1.0.0",
    "author": "Phuc NT, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Marketing",
    "website": "https://odoo-community.org/",
    'summary': "Split or merge recipients when send mail.",
    'description': """
        Configuring only one email should be sent to all recipients (convenient to know who
         else has received the email) or split recipients to send one mail for each person. 
    """,
    'depends': [
        'mail',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'data': [
        'views/mail_mail_view.xml',
        'views/mail_template_view.xml',
        'data/ir_config_parameter.xml',
    ],
    'installable': True,
}
