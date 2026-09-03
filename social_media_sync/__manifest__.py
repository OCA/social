# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Social Media Sync",
    "summary": "Import posts, figures and comments back from the social media",
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
        "data/ir_cron_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "social_media_sync/static/src/xml/**/*.xml",
            # Partials first: SCSS assets are compiled as a single unit. The
            # mixins live in social_media_base and are used without being
            # declared here, because base is compiled before its dependents.
            "social_media_sync/static/src/components/**/*.scss",
            "social_media_sync/static/src/js/services/**/*.js",
            "social_media_sync/static/src/components/**/*.xml",
            "social_media_sync/static/src/components/**/*.js",
            "social_media_sync/static/src/js/views/**/*.js",
        ],
    },
    "installable": True,
}
