# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Social Media Base",
    "summary": """Basic module for social media management.""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "BinhexTeam,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["base", "web", "mail", "utm", "crm"],
    "data": [
        "security/ir.model.access.csv",
        "security/social_account_security.xml",
        "security/social_post_security.xml",
        "security/social_post_account_security.xml",
        "data/ir_cron_data.xml",
        "views/social_media_views.xml",
        "views/social_account_views.xml",
        "views/social_post_views.xml",
        "views/social_post_account_views.xml",
        "views/social_comment_views.xml",
        "views/social_lead_views.xml",
        "views/utm_group_campaign_views.xml",
        "views/utm_campaign_views.xml",
        "views/social_action_client_views.xml",
        "wizards/wizard_social_account.xml",
        "views/social_media_base_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            ("include", "web.chartjs_lib"),
            # GENERAL
            "social_media_base/static/src/xml/**/*.xml",
            "social_media_base/static/src/scss/**/*.scss",
            # MIXINS
            "social_media_base/static/src/js/app/**/*.js",
            # SERVICES
            "social_media_base/static/src/js/services/**/*.js",
            # COMPONENTS
            "social_media_base/static/src/components/**/*.xml",
            "social_media_base/static/src/components/**/*.js",
            "social_media_base/static/src/components/**/*.scss",
            # VIEWS
            "social_media_base/static/src/js/views/**/*.xml",
            "social_media_base/static/src/js/views/**/*.scss",
            "social_media_base/static/src/js/views/**/*.js",
        ],
    },
    "excludes": ["social"],
}
