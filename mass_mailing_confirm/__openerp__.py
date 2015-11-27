# -*- coding: utf-8 -*-
# © 2015 Antiun Ingenieria S.L. - Antonio Espinosa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Mass mailing confirm",
    "summary": "User must confirm before sent a mass mailing",
    "version": "8.0.1.0.0",
    "category": "Marketing",
    "website": "http://www.antiun.com",
    "author": "Antiun Ingeniería, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mass_mailing",
    ],
    "data": [
        "views/mass_mailing_view.xml",
    ],
}
