# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Social Media Advertising",
    "summary": "Advertising campaigns, campaign groups and ads for social media.",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "development_status": "Beta",
    "license": "AGPL-3",
    "author": "Binhex, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "maintainers": ["edescalona"],
    "depends": ["social_media_base"],
    "data": [
        "security/ir.model.access.csv",
        "security/social_advertising_campaign_security.xml",
        "security/social_advertising_account_security.xml",
        "security/social_advertising_ad_security.xml",
        "data/ir_cron_data.xml",
        "views/social_account_views.xml",
        "views/social_advertising_account_views.xml",
        "views/social_tag_views.xml",
        "views/social_stage_views.xml",
        "views/social_advertising_campaign_group_views.xml",
        "views/social_advertising_campaign_views.xml",
        "views/social_post_views.xml",
        "views/social_post_account_views.xml",
        "views/social_advertising_ad_views.xml",
        "views/social_media_advertising_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "social_media_advertising/static/src/js/**/*.xml",
            "social_media_advertising/static/src/js/**/*.js",
        ],
    },
    "installable": True,
}
