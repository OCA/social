# Copyright 2017 Tecnativa - Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Default Thread For Unbounded Emails",
    "summary": "Post unkonwn messages to an existing thread",
    "version": "11.0.1.0.0",
    "category": "Discuss",
    "website": "https://www.github.com/social",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "fetchmail",
    ],
    "data": [
        "views/fetchmail_server_view.xml",
    ],
    "demo": [
        "demo/data.xml",
    ],
}
