# Copyright 2026 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail Mention Suggestion Config",
    "summary": "Configure your partner mention suggestions in chatter messages",
    "version": "18.0.1.0.0",
    "category": "Mail",
    "website": "https://github.com/OCA/social",
    "author": "Sygel, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
    ],
    "data": [
        "views/res_config_settings.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_mention_suggestion_config/static/src/js/suggestion_service.esm.js",
        ],
    },
}
