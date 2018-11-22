# -*- coding: utf-8 -*-
# Copyright 2016 Odoo SA <https://www.odoo.com>
# Copyright 2018 Therp BV <http://therp.nl>
# Copyright 2018 Eficent <http://www.eficent.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    "name": "Mail Activity Calendar",
    "version": "9.0.1.0.0",
    "author": "Odoo SA,Eficent,Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "category": "Discuss",
    "summary": "Backport of integration between activities and calendar",
    "depends": [
        'mail_activity',
        'crm',
    ],
    "data": [
        "views/mail_activity_views.xml",
        "views/calendar_event_views.xml",
        'views/calendar_templates.xml',
        "data/mail_activity_data.xml",
    ],
    "pre_init_hook": "pre_init_hook",
}
