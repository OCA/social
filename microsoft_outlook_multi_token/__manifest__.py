# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Multiple tokens for Outlook integration",
    "summary": "Allows to configure different client ids and secrets per server",
    "version": "16.0.1.0.0",
    "development_status": "Alpha",
    "category": "Extra Tools",
    "website": "https://github.com/OCA/social",
    "author": "Hunki Enterprises BV, Odoo Community Association (OCA)",
    "maintainers": ["hbrunn"],
    "license": "AGPL-3",
    "depends": [
        "microsoft_outlook",
    ],
    "data": [
        "views/fetchmail_server.xml",
        "views/ir_mail_server.xml",
    ],
}
