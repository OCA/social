# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Social Media X",
    "summary": """Integration of the X social network.""",
    "version": "18.0".1.0.0",
    "license": "AGPL-3",
    "author": "Binhex <https://www.binhex.cloud>,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": [
        "social_media_base",
    ],
    "data": [
        "data/social_media_data.xml",
        "views/social_account_views.xml",
        "wizards/wizard_social_account.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # SERVICES
            "social_media_x/static/src/js/services/**/*.js",
            # KANBAN
            "social_media_x/static/src/js/views/**/*.js",
        ],
    },
    "external_dependencies": {
        "python": [
            "tweepy",
        ],
    },
    "exclude": ["social"],
}
