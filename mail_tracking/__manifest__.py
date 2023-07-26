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
    "depends": ["mail", "im_livechat"],
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
        "web.assets_backend": [
            "mail_tracking/static/src/css/*.scss",
            "mail_tracking/static/src/js/models/*.esm.js",
            "mail_tracking/static/src/js/*.esm.js",
            "mail_tracking/static/src/components/*.xml",
        ],
    },
    "demo": ["demo/demo.xml"],
}
