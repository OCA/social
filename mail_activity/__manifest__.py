# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Activities",
    "version": "10.0.1.0.0",
    "author": "Odoo SA,Therp BV,Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "category": "Discuss",
    "summary": "Backport activities",
    "depends": [
        'mail',
    ],
    "data": [
        "data/mail_message_subtype.xml",
        'security/ir.model.access.csv',
        'views/mail_activity.xml',
        'data/mail_activity.xml',
        'data/ir_model_data.xml',
    ],
    "qweb": [
    ],
}
