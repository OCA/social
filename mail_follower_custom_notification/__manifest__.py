# Copyright 2015 Therp BV <http://therp.nl>
# Copyright 2025 Hunki Enterprises BV <https://hunki-enterprises.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Custom notification settings for followers",
    "version": "16.0.1.0.0",
    "author": "Hunki Enterprises BV,Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Social Network",
    "summary": "Let followers choose if they want to receive email "
    "notifications for a given subscription",
    "website": "https://github.com/OCA/social",
    "depends": [
        "mail",
    ],
    "data": [
        "views/mail_message_subtype.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "/mail_follower_custom_notification/static/src/components/*/*",
            "/mail_follower_custom_notification/static/src/models/*",
        ],
    },
    "installable": True,
    "uninstall_hook": "uninstall_hook",
}
