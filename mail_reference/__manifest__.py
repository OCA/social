# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "mail_reference",
    "version": "10.0.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Social",
    "summary": "Set your own delimiters on the Chatter.",
    "depends": [
        'mail',
        'web_tour',
        'web_editor',
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/mail_reference_mention.xml',
        'views/menus.xml',
        'views/assets.xml',
    ],
    "application": False,
}
