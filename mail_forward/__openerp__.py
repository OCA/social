# -*- coding: utf-8 -*-
# © 2014-2015 Grupo ESOC <www.grupoesoc.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Message Forward",
    "summary": "Add option to forward messages",
    "version": "8.0.6.0.0",
    "category": "Social Network",
    "website": "http://www.grupoesoc.es, https://odoo-community.org/",
    "author": "Grupo ESOC, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
        "web",
    ],
    "data": [
        "wizard/mail_forward.xml",
        "views/assets.xml",
    ],
    "qweb": [
        "static/src/xml/mail_forward.xml",
    ],
}
