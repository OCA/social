# -*- coding: utf-8 -*-
# Copyright 2016 Odoo SA <https://www.odoo.com>
# Copyright 2018 Therp BV <http://therp.nl>
# Copyright 2018 Eficent <http://www.eficent.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    "name": "Activities in CRM",
    "version": "9.0.1.0.0",
    "author": "Odoo SA,Therp BV,Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "category": "Discuss",
    "summary": "Backport activities in CRM",
    "depends": [
        'mail_activity',
        'mail_activity_calendar',
        'crm',
    ],
    "data": [
        "views/crm_lead_views.xml",
        'views/crm_activity_report_view.xml',
        'views/crm_lead_menu.xml',
        'views/crm_action_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
}
