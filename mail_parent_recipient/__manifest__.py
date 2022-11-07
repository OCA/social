# Copyright 2018-2022 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail parent recipient",
    "summary": "Send email to parent partner if partner's email is empty",
    "category": "Mail",
    "license": "AGPL-3",
    "version": "15.0.1.0.0",
    "website": "https://github.com/OCA/social",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
    ],
    "data": ["views/res_config_views.xml"],
}
