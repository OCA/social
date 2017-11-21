# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Bus Presence Override",
    "summary": "Adds user-defined im status (online, away, offline).",
    "version": "10.0.1.0.0",
    "category": "Social",
    "website": "https://github.com/OCA/social",
    "author": "LasLabs, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
    ],
    "data": [
        "views/assets.xml",
    ],
    "qweb": [
        "static/src/xml/systray.xml",
    ],
}
