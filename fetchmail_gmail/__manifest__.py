# Copyright 2022 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Fetchmail Gmail",
    "summary": "Backport of the fetchmail_gmail which is introduced in Odoo Community Version 12.0",
    "version": "10.0.1.0.0",
    "author": "Odoo SA, Odoo Community Association (OCA), Camptocamp",
    "license": "LGPL-3",
    "category": "Hidden",
    "description": "Google authentication for incoming mail server",
    "depends": [
        "google_gmail",
        "fetchmail",
    ],
    "data": ["views/fetchmail_server_views.xml"],
    "website": "https://github.com/OCA/social",
    "auto_install": True,
}
