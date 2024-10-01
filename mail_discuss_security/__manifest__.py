# Copyright 2015 Anubía, soluciones en la nube,SL (http://www.anubia.es)
# Copyright 2017 Onestein (http://www.onestein.eu)
# Copyright (C) 2019-Today: Druidoo (<https://www.druidoo.io>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Discuss Group",
    "summary": "Add a group to display 'Discuss' Application menu entry",
    "version": "16.0.1.0.0",
    "category": "Usability",
    "license": "AGPL-3",
    "author": "GRAP, Odoo Community Association (OCA)",
    "maintainers": ["legalsylvain"],
    "website": "https://github.com/OCA/social",
    "depends": ["mail"],
    "data": [
        "security/res_groups.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_discuss_security/static/src/js/*.js",
        ],
    },
    "installable": True,
}
