# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2018 David Vidal - <david.vidal@tecnativa.com>
# Copyright 2018 Tecnativa - Ernesto Tejeda
# Copyright 2019 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Email tracking",
    "summary": "Email tracking system for all mails sent",
    "version": "16.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": ("Tecnativa, " "Odoo Community Association (OCA)"),
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["mail"],
    "data": [
        "data/tracking_data.xml",
        "security/mail_tracking_email_security.xml",
        "security/ir.model.access.csv",
        "views/mail_tracking_email_view.xml",
        "views/mail_tracking_event_view.xml",
        "views/mail_message_view.xml",
        "views/res_partner_view.xml",
    ],
    "assets": {
        "mail.assets_messaging": [
            "mail_tracking/static/src/js/models/*.js",
        ],
        "web.assets_backend": [
            "mail_tracking/static/src/xml/mail_tracking.xml",
            "mail_tracking/static/src/css/mail_tracking.scss",
            "mail_tracking/static/src/css/failed_message.scss",
            "mail_tracking/static/src/js/message.esm.js",
            "mail_tracking/static/src/js/failed_message/mail_failed_box.esm.js",
            "mail_tracking/static/src/js/models/thread.esm.js",
            "mail_tracking/static/src/xml/mail_tracking.xml",
            "mail_tracking/static/src/xml/failed_message/common.xml",
            "mail_tracking/static/src/xml/failed_message/thread.xml",
            "mail_tracking/static/src/xml/failed_message/discuss.xml",
        ],
        "web.assets_frontend": [
            "mail_tracking/static/src/css/failed_message.scss",
        ],
    },
    "demo": ["demo/demo.xml"],
}
