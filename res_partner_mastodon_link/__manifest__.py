# Copyright (C) 2026 - Today: Sylvain LE GAL (http://www.grap.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Partner - Mastodon Link",
    "summary": "Add mastodon url at partner model",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "GRAP, OCA France, Odoo Community Association (OCA)",
    "maintainers": ["legalsylvain"],
    "website": "https://github.com/OCA/social",
    "installable": True,
    "depends": ["base_fontawesome"],
    "data": [
        "views/view_res_partner.xml",
        "views/templates.xml",
    ],
    "demo": ["demo/demo_res_partner.xml"],
    "post_init_hook": "post_init_hook",
}
