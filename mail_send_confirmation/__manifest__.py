# Copyright 2023 Quartile Limited
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail Send Confirmation",
    "version": "15.0.1.0.0",
    "author": "Quartile Limited, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Mail",
    "website": "https://github.com/OCA/social",
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "mail_send_confirmation/static/src/components/composer/composer.esm.js",
        ],
    },
    "installable": True,
}
