# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    "name": "Mail Message Purge",
    "summary": "Delete old mail messages based on configuration.",
    "version": "14.0.1.0.0",
    "category": "Mail",
    "author": "Camptocamp,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "maintainers": ["TDu"],
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "data": [
        "data/ir_cron.xml",
        "security/ir.model.access.csv",
        "views/mail_message_purge_views.xml",
    ],
}
