# -*- coding: utf-8 -*-
# Copyright 2016 Tecnativa - Jairo Llopis
# Copyright 2016 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Base for Vertical Resizing of Snippets",
    "summary": "Allow input of height in pixels with just a class",
    "version": "9.0.1.0.0",
    "category": "Website",
    "website": "http://tecnativa.com",
    "author": "Tecnativa, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "website_mail",
        "mass_mailing",
    ],
    "data": [
        "views/assets.xml",
        "views/snippets.xml",
    ],
}
