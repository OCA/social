# Copyright 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Allow Portal Users to access internal messages",
    "summary": "Portal users can access internal messages"
    " related to own or other companies",
    "version": "14.0.1.0.0",
    "category": "Social Network",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "depends": ["mail"],
    "installable": True,
    "maintainer": ["dreispt"],
    "development_status": "Alpha",
    "data": ["views/res_users.xml"],
}
