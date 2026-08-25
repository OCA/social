# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Social Media Advertising LinkedIn",
    "summary": "LinkedIn Ads campaigns, campaign groups and sponsored creatives.",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "development_status": "Beta",
    "license": "AGPL-3",
    "author": "Binhex, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "maintainers": ["edescalona"],
    "depends": ["social_media_advertising", "social_media_linkedin"],
    "data": [
        "data/social_stage_data.xml",
        "views/social_advertising_campaign_group_views.xml",
        "views/social_advertising_campaign_views.xml",
        "views/social_account_views.xml",
        "views/social_advertising_account_views.xml",
        "views/social_advertising_ad_views.xml",
        "views/social_stage_views.xml",
        "views/social_media_advertising_linkedin_menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
