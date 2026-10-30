# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail Message Import",
    "summary": "Receive messages by several channels, identify their senders "
    "and group them in conversations",
    "version": "17.0.1.0.0",
    "category": "Productivity",
    "website": "https://github.com/OCA/social",
    "author": "Binhex, Odoo Community Association (OCA)",
    "maintainers": ["oliverg09"],
    "license": "AGPL-3",
    "development_status": "Beta",
    "depends": ["mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        "views/mail_message_import_channel_views.xml",
        "views/mail_message_import_config_views.xml",
        "views/mail_message_import_sender_views.xml",
        "views/mail_message_import_message_views.xml",
        "views/mail_message_import_conversation_views.xml",
        "views/mail_message_import_incident_views.xml",
        "wizards/mail_message_import_assign_sender_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_message_import/static/src/**/*",
        ],
    },
    "application": True,
    "installable": True,
}
