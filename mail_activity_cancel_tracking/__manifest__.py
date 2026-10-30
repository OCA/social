# Copyright 2025 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail Activity Cancel Tracking",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "version": "17.0.1.0.1",
    "depends": ["mail"],
    "license": "AGPL-3",
    "category": "Social Network",
    "installable": True,
    "maintainers": ["victoralmau"],
    "data": ["data/mail_template_data.xml"],
    "assets": {
        "web.assets_tests": [
            "mail_activity_cancel_tracking/static/tests/tours/**/*",
        ]
    },
}
