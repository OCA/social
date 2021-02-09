# -*- coding: utf-8 -*-
# © 2014-2015 Grupo ESOC <www.grupoesoc.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Message Forward",
    "summary": "Add option to forward messages",
    "version": "10.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
        "web",
    ],
    "data": [
        "views/assets.xml",
        "views/compose_message.xml",
        "views/res_request_link.xml",
    ],
    "qweb": [
        "static/src/xml/mail_forward.xml",
    ],
}
