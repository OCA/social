# Copyright 2016 Tecnativa - Jairo Llopis
# Copyright 2018 Tecnativa - David Vidal
# Copyright 2020 Tecnativa - Pedro M. Baeza
# Copyright 2024 Tecnativa - Carolina Fernandez
# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Mass mailing unsubscription metadata",
    "summary": "Track metadata for GDPR compliance",
    "category": "Marketing",
    "version": "17.0.1.0.0",
    "depends": ["mass_mailing"],
    "data": [
        "views/mail_subscription_view.xml",
    ],
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "assets": {
        "web.assets_tests": [
            "mass_mailing_custom_unsubscribe/static/tests/**/*",
        ],
    },
}
