# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Email CC and BCC when sending invoice",
    "summary": "This module enables sending mail to CC and BCC partners for invoices.",
    "version": "17.0.1.0.0",
    "development_status": "Alpha",
    "category": "Social",
    "website": "https://github.com/OCA/social",
    "author": "Camptocamp SA, Odoo Community Association (OCA)",
    "maintainers": ["hailangvn2023"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "auto_install": True,
    "preloadable": True,
    "depends": [
        "account",
        "mail_composer_cc_bcc",
    ],
    "data": [
        "wizards/account_move_send.xml",
    ],
}
