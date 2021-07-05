# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Embed Image",
    "version": "10.0.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Social",
    "summary": "Replace img.src's which start with http with inline cids",
    "depends": [
        'web',
    ],
    "external_dependencies": [
        'beautifulsoup4'
    ],
    "installable": True,
    "application": False,
}
