# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Email CC and BCC when sending invoice",
    "summary": "This module enables sending mail to CC and BCC partners for invoices.",
    "version": "16.0.2.0.0",
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
        "mail_composer_cc_bcc",
        "account",
    ],
    "data": [
        "wizards/account_invoice_send_views.xml",
    ],
}
