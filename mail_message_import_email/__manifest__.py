# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail Message Import - Email",
    "summary": "Receive by email the messages of Mail Message Import",
    "version": "17.0.1.0.0",
    "category": "Productivity",
    "website": "https://github.com/OCA/social",
    "author": "Binhex, Odoo Community Association (OCA)",
    "maintainers": ["oliverg09"],
    "license": "AGPL-3",
    "development_status": "Beta",
    "depends": ["mail_message_import"],
    "data": [
        "views/mail_message_import_channel_views.xml",
        "views/mail_message_import_message_views.xml",
    ],
    "installable": True,
}
