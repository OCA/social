# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Social Media Calendar",
    "summary": "Calendar view of the posts, placed on their date and coloured by state",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "development_status": "Beta",
    "license": "AGPL-3",
    "author": "Binhex, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "maintainers": ["edescalona"],
    "depends": ["social_media_base"],
    "data": [
        "views/social_post_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "social_media_calendar/static/src/js/views/**/*.js",
        ],
    },
    "auto_install": True,
    "installable": True,
}
