# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Social Media LinkedIn Sync",
    "summary": "Import LinkedIn publications, their figures, comments and reactions",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "development_status": "Beta",
    "license": "AGPL-3",
    "author": "Binhex, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "maintainers": ["edescalona"],
    "depends": ["social_media_sync", "social_media_linkedin"],
    "data": [
        "views/social_account_views.xml",
    ],
    "assets": {
        "web.assets_tests": [
            "social_media_linkedin_sync/static/tests/tours/**/*.js",
        ],
        "web.assets_backend": [
            "social_media_linkedin_sync/static/src/components/**/*.js",
            "social_media_linkedin_sync/static/src/js/views/**/*.js",
        ],
    },
    "auto_install": True,
    "installable": True,
}
