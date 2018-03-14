# -*- coding: utf-8 -*-
# © 2016 Sunflower IT (http://sunflowerweb.nl)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Message Edit",
    "summary": "Adds an option to edit mail to different partners",
    "version": "8.0.1.0.0",
    "category": "Social Network",
    "website": "https://sunflowerweb.nl",
    "author": "Sunflower IT, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
        "web",
    ],
    "data": [
        "security/mail_edit_security.xml",
        "views/assets.xml",
        "views/compose_message.xml",
        "views/res_request_link.xml",
    ],
    "qweb": [
        "static/src/xml/mail_edit.xml",
    ],
}
