# Copyright 2025 Kencove - Mohamed Alkobrosli
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Template Editor",
    "summary": "Using web editor for mail template",
    "version": "16.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": ("Kencove, Odoo Community Association (OCA)"),
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["mail", "mass_mailing"],
    "data": [
        "views/mail_template_views.xml",
        "views/mailing_mailing_views.xml",
    ],
}
