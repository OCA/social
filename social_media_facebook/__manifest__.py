# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Social Media Facebook",
    "summary": """Integration of the Facebook social network.""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Odoo Community Association (OCA)",
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
        "views/res_config_settings_views.xml",
        "views/social_account_views.xml",
        "views/social_post_views.xml",
        "views/social_post_account_views.xml",
        "views/social_lead_views.xml",
        "views/utm_campaign_views.xml",
        "views/social_media_facebook_menus.xml",
        "views/social_media_views.xml",
        "wizards/wizard_facebook_sync.xml",
        "wizards/wizard_fetch_pages.xml",
        "wizards/wizard_social_account.xml",
        "wizards/wizard_facebook_system_user.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # STYLES
            "social_media_facebook/static/src/scss/facebook_dashboard.scss",
            "social_media_facebook/static/src/scss/facebook_post.scss",
            # SERVICES
            "social_media_facebook/static/src/js/services/**/*.js",
            # COMPONENTS
            "social_media_facebook/static/src/components/**/*.js",
            # KANBAN
            "social_media_facebook/static/src/js/views/**/*.js",
            # DASHBOARD - Account cards with sync button
            "social_media_facebook/static/src/js/social_account_facebook.esm.js",
            "social_media_facebook/static/src/xml/dashboard_templates.xml",
        ],
    },
    "exclude": ["social"],
}
