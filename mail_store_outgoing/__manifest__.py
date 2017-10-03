# -*- coding: utf-8 -*-
{
    "name" : "outgoing_mail_save",
    "version" : "1.0",
    "author" : "Agent ERP GmbH",
    "category": 'mail',
    'complexity': "easy",
    "description": """
This Module saves all outgoing mails to the Mailserver via IMAP
====================================
v1.0
    """,
    'website': 'www.agenterp.com',
    "depends" : ["base","mail"],
    'init_xml': [],
    'update_xml': [
        'views/ir_mail_server_view.xml',
        'security/ir.model.access.csv'],
    'demo_xml': [],
    'test': [],
    'application': True,
    'installable': True,
    'css': [
    ],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

