# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail activity plan",
    "version": "16.0.1.0.1",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["mail"],
    "installable": True,
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/mail_activity_plan_views.xml",
        "wizards/wizard_mail_activity_views.xml",
    ],
    "demo": ["demo/mail_activity_plan_demo.xml"],
    "assets": {
        "web.assets_backend": [
            "mail_activity_plan/static/src/js/mail_activity_plan.esm.js",
        ],
    },
    "maintainers": ["victoralmau"],
}
