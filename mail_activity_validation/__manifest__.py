# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail Activity Validation",
    "version": "17.0.1.0.0",
    "category": "Discuss",
    "website": "https://github.com/OCA/social",
    "author": "Camptocamp SA, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "application": False,
    "summary": "Allow to define validation activities",
    "depends": [
        "mail",
    ],
    "data": [
        "views/mail_activity_type.xml",
    ],
}
