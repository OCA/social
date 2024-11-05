# Copyright 2020 Valentin Vinagre <valentin.vinagre@sygel.es>
# Copyright 2022 Eduardo de Miguel <edu@moduon.team>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail Show Follower",
    "summary": "Show CC document followers in mails.",
    "version": "16.0.1.1.1",
    "category": "Mail",
    "website": "https://github.com/OCA/social",
    "author": "Sygel, Moduon, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["base", "mail"],
    "maintainers": ["yajo"],
    "data": [
        "views/res_config_settings.xml",
        "views/res_users.xml",
    ],
}
