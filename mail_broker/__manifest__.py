# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Broker",
    "summary": """
        Set a broker""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "Creu Blanca,Dixmit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mail"],
    "pre_init_hook": "pre_init_hook",
    "data": [
        "wizards/mail_message_broker_send.xml",
        "wizards/mail_guest_manage.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/mail_broker.xml",
        "views/res_partner.xml",
    ],
    "assets": {
        "mail.assets_messaging": [
            "mail_broker/static/src/models/**/*.js",
        ],
        "web.assets_backend": [
            "mail_broker/static/src/components/**/*.xml",
        ],
        "mail.assets_discuss_public": [
            "mail_broker/static/src/components/**/*.xml",
        ],
    },
}
