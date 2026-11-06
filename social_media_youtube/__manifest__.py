# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Social Media YouTube",
    "summary": "Integration of the YouTube social network.",
    "version": "19.0.1.0.0",
    "category": "Social Network",
    "development_status": "Beta",
    "license": "AGPL-3",
    "author": "Domatix, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "maintainers": ["idris-domatix"],
    "depends": [
        "social_media_base",
    ],
    "data": [
        "data/social_media_data.xml",
        "views/social_account_views.xml",
        "views/social_post_views.xml",
        "wizards/wizard_social_account.xml",
    ],
    "external_dependencies": {
        "python": [
            "requests",
        ],
    },
    "excludes": ["social"],
    "installable": True,
}
