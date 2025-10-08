# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Social Media Linkedin",
    "summary": """Integration of the LinkedIn social network.""",
    "version": "17.0.1.0.0",
    "license": "AGPL-3",
    "author": "Binhex <https://www.binhex.cloud>,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": [
        "social_media_base",
    ],
    "data": [
        "data/social_media_data.xml",
        "views/social_post_account_views.xml",
        "views/social_account_views.xml",
        "views/utm_group_campaign_views.xml",
        "views/utm_campaign_views.xml",
        "wizards/wizard_social_account.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # COMPONENTS
            "social_media_linkedin/static/src/components/**/*.js",
            # SERVICES
            "social_media_linkedin/static/src/js/services/**/*.js",
            # KANBAN
            "social_media_linkedin/static/src/js/views/**/*.js",
        ],
    },
    "external_dependencies": {
        "python": [
            "linkedin-api-client",
        ],
    },
    "exclude": ["social"],
}
