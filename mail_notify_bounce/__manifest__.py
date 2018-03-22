# -*- coding: utf-8 -*-
# Copyright 2017 Lorenzo Battistini - Agile Business Group
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Notify bounce emails",
    "summary": "Notify bounce emails to preconfigured addresses",
    "version": "10.0.1.0.2",
    "category": "Mail",
    "website": "https://github.com/OCA/social",
    "author": "Agile Business Group, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "fetchmail",
    ],
    "data": [
        "views/fetchmail_view.xml",
    ],
}
