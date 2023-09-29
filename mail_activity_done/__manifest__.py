# Copyright 2018-22 ForgeFlow <http://www.forgeflow.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    "name": "Mail Activity Done",
    "version": "16.0.1.1.0",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "category": "Discuss",
    "website": "https://github.com/OCA/social",
    "depends": ["mail"],
    "data": ["views/mail_activity_views.xml"],
    "assets": {
        "web.assets_backend": [
            "mail_activity_done/static/src/js/mail_activity.esm.js",
        ],
    },
    "pre_init_hook": "pre_init_hook",
    "uninstall_hook": "uninstall_hook",
}
