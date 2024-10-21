# Copyright 2024 CorporateHub
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail Thread Post Access",
    "summary": (
        "Allows to permit posting notes and messages to users that don't have"
        " write access to the record"
    ),
    "version": "17.0.1.0.0",
    "category": "Productivity/Discuss",
    "website": "https://github.com/OCA/social",
    "author": "CorporateHub, Odoo Community Association (OCA)",
    "maintainers": ["alexey-pelykh"],
    "license": "AGPL-3",
    "depends": [
        "base",
        "mail",
    ],
    "data": [
        "views/ir_model.xml",
    ],
}
