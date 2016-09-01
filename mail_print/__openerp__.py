# -*- coding: utf-8 -*-
# © initOS GmbH 2016
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "Print Emails",
    'summary': """
        PDF Reports to print the emails
        """,
    'author': "initOS GmbH, Odoo Community Association (OCA)",
    'website': "http://www.initos.com",
    'version': '8.0.1.0.0',
    'license': 'AGPL-3',
    'depends': [
        'report',
        'mail',
        'web',
        ],
    'data': [
        'report.xml',
        'views/mail_message_report.xml',
        'views/templates.xml',
        ],
    'qweb': [
        'static/src/xml/mail.xml',
    ],
}
