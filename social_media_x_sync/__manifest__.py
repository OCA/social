# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Social Media X Sync",
    "summary": "Import the X timeline, its figures and the conversation of each post",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "development_status": "Beta",
    "license": "AGPL-3",
    "author": "Binhex, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "maintainers": ["edescalona"],
    "depends": [
        "social_media_sync",
        "social_media_x",
    ],
    "data": [
        "views/social_account_views.xml",
        "views/social_post_account_views.xml",
    ],
    "assets": {
        "web.assets_tests": [
            "social_media_x_sync/static/tests/tours/**/*.js",
        ],
        "web.assets_backend": [
            "social_media_x_sync/static/src/js/views/**/*.js",
        ],
    },
    "auto_install": True,
    "installable": True,
}
