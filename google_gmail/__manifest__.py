# Copyright 2022 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Google Gmail",
    "summary": "Backport of the google_gmail which is introduced in Odoo Community Version 12.0",
    "version": "10.0.1.0.0",
    "author": "Odoo SA, Odoo Community Association (OCA), Camptocamp",
    "license": "LGPL-3",
    "category": "Hidden",
    "description": "Gmail support for incoming / outgoing mail servers",
    "depends": [
        "mail",
        "google_account",
        "base_ir_mail_server",
    ],
    "data": [
        "views/ir_mail_server_views.xml",
        "views/res_config_views.xml",
    ],
    "external_dependencies": {"python": ["requests"]},
    "website": "https://github.com/OCA/social",
    "auto_install": True,
}
