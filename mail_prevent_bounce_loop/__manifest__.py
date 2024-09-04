# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Prevent Bounce Loop",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "category": "Social Network",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "version": "17.0.1.0.0",
    "depends": ["mail"],
    "data": [
        "views/res_partner.xml",
    ],
}
