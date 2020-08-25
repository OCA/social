# Copyright 2020 Adhoc SA.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Mail Outbound Dynamic",
    "summary": "Allows you to configure the from header for a mail server.",
    "version": "13.0.1.0.1",
    "category": "Discuss",
    "website": "https://github.com/OCA/social",
    "author": "Adhoc SA, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "depends": ["base"],
    "data": [
        "views/ir_mail_server_view.xml",
    ],
}
