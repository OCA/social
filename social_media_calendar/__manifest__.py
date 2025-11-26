# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Social Media Calendar",
    "summary": """Module for social media calendar integration.""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "BinhexTeam,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["social_media_base", "calendar"],
    "data": [
        "views/social_post_views.xml",
    ],
    "exclude": ["social"],
    "auto_install": True,
}
