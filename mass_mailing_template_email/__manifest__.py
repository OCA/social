# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Mass Mailing Templates",
    "version": "10.0.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "social",
    "summary": "Use email templates on mass mailing.",
    "depends": [
        'mail',
        'mass_mailing',
        'web',
    ],
    "data": [
        'data/ir_ui_view.xml',
        'views/menus.xml',
        'views/editor_field_html.xml',
    ],
    "application": True,
}
