# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Rate limit mail sending",
    "version": "8.0.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Tools",
    "summary": "Send only a fixed amount of mails per queue run",
    "depends": [
        'mail',
    ],
    "data": [
        "data/ir_config_parameter.xml",
    ],
}
