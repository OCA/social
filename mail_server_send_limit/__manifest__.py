# Copyright 2025 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Server Send Limit",
    "summary": "Limit number of email sent by hour by email server",
    "version": "16.0.1.0.0",
    "development_status": "Alpha",
    "category": "Productivity/Discuss",
    "website": "https://github.com/OCA/social",
    "author": "Sergio Corato, Odoo Community Association (OCA)",
    "maintainers": ["sergiocorato"],
    "license": "AGPL-3",
    "depends": [
        "mass_mailing",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/ir_mail_server.xml",
    ],
}
