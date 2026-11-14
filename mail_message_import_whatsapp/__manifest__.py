# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail Message Import - WhatsApp",
    "summary": "Receive by WhatsApp the messages of Mail Message Import",
    "version": "18.0.1.0.0",
    "category": "Productivity",
    "website": "https://github.com/OCA/social",
    "author": "Binhex, Odoo Community Association (OCA)",
    "maintainers": ["oliverg09"],
    "license": "AGPL-3",
    "development_status": "Beta",
    "depends": ["mail_message_import", "mail_gateway_whatsapp"],
    "external_dependencies": {"python": ["phonenumbers"]},
    "data": [
        "views/mail_message_import_channel_views.xml",
        "views/mail_message_import_message_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
}
