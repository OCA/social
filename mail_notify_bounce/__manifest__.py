# Copyright 2017 Lorenzo Battistini - Agile Business Group
# Copyright 2022 Simone Vanin - Agile Business Group
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Notify bounce emails",
    "summary": "Notify bounce emails to preconfigured addresses",
    "version": "14.0.1.0.0",
    "category": "Mail",
    "website": "https://github.com/OCA/social",
    "author": "Agile Business Group, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "fetchmail",
    ],
    "data": [
        "views/fetchmail_view.xml",
    ],
}
