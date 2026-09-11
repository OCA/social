# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Social Media Linkedin",
    "summary": "Publish on the LinkedIn pages you administrate, with daily figures",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "development_status": "Beta",
    "license": "AGPL-3",
    "uninstall_hook": "uninstall_hook",
    "author": "Binhex, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "maintainers": ["edescalona"],
    "depends": [
        "social_media_base",
    ],
    "data": [
        "data/social_media_data.xml",
        "views/social_account_views.xml",
        "wizards/wizard_social_account.xml",
    ],
    "installable": True,
}
