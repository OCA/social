# Copyright 2017 Tecnativa - Jairo Llopis <jairo.llopis@tecnativa.com>
# Copyright 2023-24 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Default Thread For Unbounded Emails",
    "summary": "Post unkonwn messages to an existing thread",
    "version": "16.0.1.0.0",
    "category": "Discuss",
    "website": "https://github.com/OCA/social",
    "author": "Tecnativa, Therp BV,  Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["mail"],
    "data": ["views/fetchmail_server_view.xml"],
    "demo": ["demo/data.xml"],
}
