# Copyright 2024 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Forward Message",
    "version": "15.0.1.0.1",
    "summary": "Forward messages from the chatter of any document to other users.",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mail", "contacts"],
    "data": [
        "wizards/mail_compose_message_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_forward/static/src/components/**/*.esm.js",
        ],
        "web.assets_qweb": [
            "mail_forward/static/src/components/*/*.xml",
        ],
        "web.assets_tests": [
            "mail_forward/static/tests/tours/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
