# -*- coding: utf-8 -*-
# © 2015 Antiun Ingeniería, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Exclude opt-out contacts in mass mailing",
    "summary": "Do it by default when selecting contacts to be mailed",
    "version": "8.0.1.0.0",
    "category": "Social Network",
    "website": "https://odoo-community.org/",
    "author": "Antiun Ingeniería, S.L., Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mass_mailing",
    ],
    "data": [
        "views/mass_mailing.xml",
    ],
}
