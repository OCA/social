# © 2016-24 Sunflower IT (http://sunflowerweb.nl)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Message Edit",
    "summary": "Edit, Delete or Move messages to any model",
    "version": "16.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "Sunflower IT, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
        "web",
        "web_tour",
        "contacts",
    ],
    "data": [
        "security/mail_edit_security.xml",
        "views/compose_message.xml",
    ],
    "demo": ["demo/data.xml"],
    "assets": {
        "mail.assets_messaging": [
            "mail_edit/static/src/components/message/mail_edit.esm.js",
        ],
        "web.assets_tests": [
            "mail_edit/static/src/tests/tours/*.esm.js",
        ],
        "web.qunit_suite_tests": [
            "mail_edit/static/src/tests/qunit_suite_tests/*.esm.js",
        ],
    },
}
