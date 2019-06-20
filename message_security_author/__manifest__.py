# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Message Security Author",
    "summary": "The edition/deletion of messages is restricted",
    "version": "11.0.1.0.0",
    "category": "Social Network",
    "website": "http://github.com/OCA/social",
    "author": "Eficent, "
              "Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "application": False,
    'installable': True,
    "depends": [
        "mail",
    ],
    "data": [
        "security/security.xml",
    ],
    'maintainers': ['mreficent'],
}
