# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Social Media Calendar",
    "summary": "Module for social media calendar integration.",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "development_status": "Beta",
    "license": "AGPL-3",
    "uninstall_hook": "uninstall_hook",
    "author": "BinhexTeam,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "maintainers": ["edescalona"],
    "depends": ["social_media_base", "calendar"],
    "data": [
        "views/social_post_views.xml",
    ],
    "exclude": ["social"],
    "auto_install": True,
    "installable": True,
}
