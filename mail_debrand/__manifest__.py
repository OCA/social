# -*- coding: utf-8 -*-
# Copyright 2016 Tecnativa - Jairo Llopis
# Copyright 2017 SerpentCS - Darshan Patel
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Debrand",
    "summary": "Remove Odoo branding in sent emails",
    "version": "9.0.1.0.0",
    "category": "Social Network",
    "website": "https://www.tecnativa.com",
    "author": "Tecnativa, "
              "Eficent, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "data": ["data/mail_data.xml"],
    "depends": [
        "mail",
    ],
}
