# Copyright 2020 Valentin Vinagre <valentin.vinagre@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail Show Follower",
    "summary": "Show CC document followers in mails.",
    "version": "15.0.1.0.0",
    "category": "Mail",
    "website": "https://github.com/OCA/social",
    "author": "Sygel, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["base", "mail"],
    "data": [
        "views/res_config_settings.xml",
        "views/res_users.xml",
    ],
}
