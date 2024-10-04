# Copyright 2024 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Print Message",
    "version": "15.0.1.0.1",
    "summary": "Print messages from the chatter of any document. ",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mail", "contacts"],
    "data": [
        "data/report_paperformat_data.xml",
        "reports/report_mail_message.xml",
        "reports/reports.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_print/static/src/components/**/*.esm.js",
        ],
        "web.assets_qweb": [
            "mail_print/static/src/components/*/*.xml",
        ],
        "web.assets_tests": [
            "mail_print/static/tests/tours/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
