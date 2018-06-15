# -*- coding: utf-8 -*-
# © 2018 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
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
}
