# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Social Media Facebook",
    "summary": """Integration of the Facebook social network.""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Binhex <https://www.binhex.cloud>,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": [
        "social_media_base",
        "mail",
        "crm",
        "utm",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/social_media_data.xml",
        "data/ir_cron_data.xml",
        "views/social_account_views.xml",
        "views/social_post_views.xml",
        "views/social_comment_views.xml",
        "views/social_lead_views.xml",
        "wizards/wizard_fetch_pages.xml",
        "wizards/wizard_social_account.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # SERVICES
            "social_media_facebook/static/src/js/services/**/*.js",
            # KANBAN
            "social_media_facebook/static/src/js/views/**/*.js",
        ],
    },
    "exclude": ["social"],
}
