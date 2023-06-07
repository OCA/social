# Copyright 2023 Domatix - Jinye Ji
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Mass Mailing Newsletter Sale",
    "summary": "When a sale is paid in the website, the partner is subscribed\
        to the selected newsletter.",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "Domatix, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "category": "Social",
    "depends": ["mass_mailing", "website_sale"],
    "data": [
        "views/res_config_settings.xml",
    ],
    "qweb": [],
    "demo": [],
    "test": [],
    "installable": True,
}
