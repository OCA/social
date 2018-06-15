# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Activities in CRM",
    "version": "9.0.1.0.0",
    "author": "Odoo SA,Therp BV,Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "category": "Discuss",
    "summary": "Backport activities",
    "depends": [
        'mail_activity',
        'mail_activity_calendar',
        'crm',
    ],
    "data": [
        "views/crm_lead_views.xml",
    ],
}
