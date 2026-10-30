# Copyright (C) 2026 - Today: Sylvain LE GAL (http://www.grap.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Partner - LinkedIn Link",
    "summary": "Add LinkedIn url at partner model",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "GRAP, OCA France, Odoo Community Association (OCA)",
    "maintainers": ["legalsylvain"],
    "website": "https://github.com/OCA/social",
    "installable": True,
    "depends": ["base"],
    "data": [
        "views/view_res_partner.xml",
        "views/templates.xml",
    ],
    "demo": ["demo/demo_res_partner.xml"],
}
