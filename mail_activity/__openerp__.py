# -*- coding: utf-8 -*-
# Copyright 2016 Odoo SA <https://www.odoo.com>
# Copyright 2018 Therp BV <http://therp.nl>
# Copyright 2018 Eficent <http://www.eficent.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    "name": "Activities",
    "version": "9.0.1.0.0",
    "author": "Odoo SA,Therp BV,Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "category": "Discuss",
    "summary": "Backport activities",
    "depends": [
        'mail',
        'web_kanban',
    ],
    "data": [
        "views/res_partner.xml",
        "data/mail_message_subtype.xml",
        'security/ir.model.access.csv',
        'views/mail_activity.xml',
        'data/mail_activity.xml',
        'data/ir_model_data.xml',
        'views/templates.xml',
    ],
    "qweb": [
        'static/src/xml/mail_activity.xml',
        'static/src/xml/systray.xml',
        'static/src/xml/web_kanban_activity.xml',
    ],
    "post_load": "post_load_hook",
}
