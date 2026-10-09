# Copyright 2025 Quartile
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "IAP Mail Domain BlackList",
    "summary": "Add domains to the mail domain blacklist",
    "version": "15.0.1.0.0",
    "author": "Quartile, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "depends": ["iap"],
    "data": [
        "data/config_parameter.xml",
        "views/res_config_settings_views.xml",
    ],
    "post_load": "post_load_hook",
    "maintainers": ["yostashiro", "aungkokolin1997"],
    "installable": True,
}
