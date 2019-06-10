# Copyright 2017 Georg Notter, Agent ERP GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail Store Outgoing",
    "summary": "Store outgoing Mails via IMAP into a selected folder.",
    "version": "12.0.1.0.0",
    "category": "mail",
    "website": "https://github.com/OCA/social",
    "author": "Agent ERP GmbH, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
    ],
    "data": [
        'views/ir_mail_server_view.xml',
        'security/ir.model.access.csv',
    ],
}
