# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Mass mailing sending queue",
    "summary": "A new queue for sending mass mailing",
    "version": "8.0.1.0.0",
    "category": "Marketing",
    "website": "https://odoo-community.org/",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mass_mailing",
    ],
    "data": [
        "data/ir_config_parameter.xml",
        "data/ir_cron.xml",
        "security/ir.model.access.csv",
        "views/mass_mailing_sending_view.xml",
        "views/mass_mailing_view.xml",
    ],
}
