# -*- coding: utf-8 -*-
# Copyright 2017 Tecnativa - Jairo Llopis
# Copyright 2018 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Dynamic Mass Mailing Lists",
    "summary": "Mass mailing lists that get autopopulated",
    "version": "10.0.1.1.1",
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
        # This should go first
        "wizards/mail_mass_mailing_load_filter_views.xml",
        "views/mail_mass_mailing_list_view.xml",
    ],
}
