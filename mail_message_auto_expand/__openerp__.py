# -*- coding: utf-8 -*-
# © 2016 Sunflower IT (http://sunflowerweb.nl)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Message Auto Expand",
    "summary": "Expands the Read More Automatically",
    "version": "8.0.1.0.0",
    "category": "Social Network",
    "website": "https://sunflowerweb.nl",
    "author": "Sunflower IT, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
    ],
    "data": [],
    "qweb": [
            "static/src/xml/mail_autoexpand.xml",
        ],
}
