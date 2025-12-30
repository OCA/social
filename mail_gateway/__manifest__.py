# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Gateway",
    "summary": "Base module for gateway communications",
    "version": "18.0.1.0.4",
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
        "views/mail_guest_views.xml",
        "views/res_users_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_gateway/static/src/components/**/*",
            "mail_gateway/static/src/core/**/*",
            "mail_gateway/static/src/models/**/*",
        ],
    },
}
