# Copyright 2025 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Notification Link",
    "summary": "Navigate to document by clicking on notification name",
    "version": "17.0.1.0.0",
    "development_status": "Beta",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "mail_notification_link/static/src/notification_item.esm.js",
            "mail_notification_link/static/src/notification_item.xml",
            "mail_notification_link/static/src/messaging_menu.xml",
        ],
    },
}
