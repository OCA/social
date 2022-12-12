# Copyright 2018-20 ForgeFlow <http://www.forgeflow.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    "name": "Mail Activity Done",
    "version": "14.0.1.0.2",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "category": "Discuss",
    "website": "https://github.com/OCA/social",
    "depends": ["mail"],
    "data": ["views/templates.xml", "views/mail_activity_views.xml"],
    "pre_init_hook": "pre_init_hook",
    "post_load": "post_load_hook",
    "uninstall_hook": "uninstall_hook",
}
