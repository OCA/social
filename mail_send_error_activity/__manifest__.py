# Copyright (C) Cetmix OU <http://www.cetmix.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Set activity on mail send error",
    "version": "14.0.1.0.0",
    "author": "Cetmix,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "summary": "Set activity on mail send error",
    "depends": ["mail"],
    "data": [
        "data/mail_activity_data.xml",
        "views/assets.xml",
        "views/res_config_settings_view.xml",
    ],
    "installable": True,
}
