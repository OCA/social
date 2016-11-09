# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mass mailing event",
    "summary": "Link mass mailing with event for excluding recipients",
    "version": "8.0.1.0.0",
    "category": "Marketing",
    "website": "https://odoo-community.org/",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mass_mailing",
        "event",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/event_state_data.xml",
        "views/mass_mailing_view.xml",
    ],
}
