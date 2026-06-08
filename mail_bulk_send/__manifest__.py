# Copyright 2026 Quartile Limited
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail Bulk Send",
    "summary": "Send emails in bulk using a mail template",
    "category": "Email",
    "version": "15.0.1.0.0",
    "author": "Quartile, Odoo Community Association (OCA)",
    "maintainers": ["nobuQuartile"],
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/mail_bulk_send_wizard_views.xml",
    ],
    "installable": True,
}
