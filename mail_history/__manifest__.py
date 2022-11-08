# Copyright 2020 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Email History",
    "summary": "Module to see old messages",
    "version": "12.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "Tecnativa, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    'installable': True,
    "depends": [
        "mail",
    ],
    "qweb": [
        "static/src/xml/thread.xml",
        "static/src/xml/discuss.xml",
    ],
    "data": [
        "views/assets.xml",
    ],
    "post_init_hook": "post_init_hook",
}
