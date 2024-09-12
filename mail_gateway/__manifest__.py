# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Gateway",
    "summary": """
        Set a gateway""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "Creu Blanca,Dixmit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mail"],
    "pre_init_hook": "pre_init_hook",
    "data": [
        "wizards/mail_compose_gateway_message.xml",
        "wizards/mail_message_gateway_link.xml",
        "wizards/mail_message_gateway_send.xml",
        "wizards/mail_guest_manage.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/mail_gateway.xml",
        "views/res_partner_gateway_channel.xml",
    ],
    "assets": {
        "mail.assets_messaging": [
            "mail_gateway/static/src/models/**/*.js",
        ],
        "web.assets_backend": [
            "mail_gateway/static/src/components/**/*.xml",
            "mail_gateway/static/src/components/**/*.js",
            "mail_gateway/static/src/components/**/*.scss",
        ],
        "mail.assets_discuss_public": [
            "mail_gateway/static/src/components/**/*.xml",
            "mail_gateway/static/src/components/**/*.js",
            "mail_gateway/static/src/components/**/*.scss",
        ],
    },
}
