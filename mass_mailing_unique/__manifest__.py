# -*- coding: utf-8 -*-
# Copyright 2015 Grupo ESOC Ingeniería de Servicios, S.L.U. - Jairo Llopis
# Copyright 2016 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Unique records for mass mailing",
    "summary": "Avoids duplicate mailing lists and contacts",
    "version": "10.0.1.0.0",
    "category": "Marketing",
    "website": "https://tecnativa.com",
    "author": "Tecnativa, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "pre_init_hook": "pre_init_hook",
    "images": [
        "images/error-duplicated-email.png",
        "images/error-duplicated-list.png",
    ],
    "depends": [
        "mass_mailing",
    ],
}
