# -*- coding: utf-8 -*-
# Copyright 2018 Lorenzo Battistini - Agile Business Group
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Email: force queue",
    "summary": "Force outgoing emails to be queued",
    "version": "10.0.0.2.0",
    "category": "Discuss",
    "website": "https://github.com/OCA/social",
    "author": "Agile Business Group, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
    ],
    "data": [
        "views/res_config_view.xml",
    ],
}
