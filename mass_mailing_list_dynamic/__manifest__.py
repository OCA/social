# -*- coding: utf-8 -*-
# Copyright 2017 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Dynamic Mass Mailing Lists",
    "summary": "Mass mailing lists that get autopopulated",
    "version": "10.0.1.0.0",
    "category": "Marketing",
    "website": "https://github.com/OCA/social",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mass_mailing_partner",
    ],
    "data": [
        "views/mail_mass_mailing_list_view.xml",
    ],
}
