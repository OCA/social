# Copyright 2022 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Whatsapp Gateway",
    "summary": "Set a gateway for WhatsApp",
    "version": "18.0.2.1.6",
    "license": "AGPL-3",
    "author": "Creu Blanca, Dixmit, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mail_gateway", "phone_validation"],
    "external_dependencies": {"python": ["requests_toolbelt"]},
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/ir_actions_server_views.xml",
        "wizards/whatsapp_composer.xml",
        "wizards/mail_compose_gateway_message.xml",
        "views/mail_whatsapp_template_views.xml",
        "views/mail_gateway.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_gateway_whatsapp/static/src/components/**/*",
        ],
    },
}
