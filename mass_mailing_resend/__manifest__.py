# Copyright 2017-2018 Tecnativa - Pedro M. Baeza
# Copyright 2018 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Resend mass mailings",
    "version": "12.0.1.0.0",
    "category": "Marketing",
    "website": "https://github.com/OCA/social",
    "author": "Tecnativa, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mass_mailing",
    ],
    "data": [
        "views/mass_mailing_views.xml",
    ],
}
