# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2018 Tecnativa - David Vidal
# Copyright 2018 Tecnativa - Ernesto Tejeda
# Copyright 2019 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Email tracking",
    "summary": "Email tracking system for all mails sent",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": ("Tecnativa, Odoo Community Association (OCA)"),
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
        "web.assets_backend": [
            "mail_tracking/static/src/core/chatter/*",
            "mail_tracking/static/src/core/message/*",
            "mail_tracking/static/src/core/search/*",
            "mail_tracking/static/src/core/discuss/*",
            "mail_tracking/static/src/services/*",
            "mail_tracking/static/src/components/message_tracking/*",
            "mail_tracking/static/src/components/failed_message/*",
            "mail_tracking/static/src/components/failed_message_review/*",
            "mail_tracking/static/src/components/failed_messages_panel/*",
        ],
    },
    "demo": ["demo/demo.xml"],
}
