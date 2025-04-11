# Copyright 2025 ForgeFlow
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail Mailgun",
    "summary": "Enable Mailgun API for email delivery as an alternative to SMTP.",
    "version": "16.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["mail"],
    "data": [
        "views/ir_mail_server_views.xml",
    ],
}
