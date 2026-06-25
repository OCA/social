# Copyright 2022 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Activity Security",
    "summary": "Control who can perform actions on activities",
    "version": "15.0.1.0.0",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "maintainers": ["ivantodorovich"],
    "license": "AGPL-3",
    "category": "Marketing",
    "website": "https://github.com/OCA/social",
    "depends": ["mail"],
    "data": ["views/mail_activity_type.xml"],
    "assets": {
        "mail.assets_discuss_public": [
            "mail_activity_security/static/src/models/**/*.js",
        ],
        "web.assets_backend": [
            "mail_activity_security/static/src/models/**/*.js",
        ],
        "web.assets_qweb": [
            "mail_activity_security/static/src/components/**/*.xml",
        ],
        "web.qunit_suite_tests": [
            "mail_activity_security/static/tests/*.js",
        ],
    },
}
