# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Make emails for to, cc and bcc visible",
    "summary": "Save and show the actual email addresses used in mail.message.",
    "version": "16.0.1.0.0",
    "development_status": "Alpha",
    "category": "Social",
    "website": "https://github.com/OCA/social",
    "author": "Therp BV, Odoo Community Association (OCA)",
    "maintainers": ["NL66278"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
        "test_mail",
        "mail_composer_cc_bcc",
    ],
    "data": [
        "views/mail_message_views.xml",
    ],
}
