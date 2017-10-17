# -*- coding: utf-8 -*-
# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2016 Tecnativa - Carlos Dauden
# Copyright 2017 Tecnativa - Pedro M. Baeza
# Copyright 2017 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Mail tracking for Mailgun",
    "summary": "Mail tracking and Mailgun webhooks integration",
    "version": "10.0.1.1.0",
    "category": "Social Network",
    "website": "https://odoo-community.org/",
    "author": "Tecnativa, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    'installable': True,
    "depends": [
        "mail_tracking",
    ],
    "data": [
        "views/res_partner.xml",
        "views/mail_tracking_email.xml",
    ]
}
