# Copyright 2023 Solvti sp. z o.o. (https://solvti.pl)
# Copyright 2025 Therp BV (https://therp.nl)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail Alias With Domain",
    "summary": "Allow simple mail alias to be combined with a mail domain",
    "author": "Solvti, Therp BV, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "post_init_hook": "init_alias_entry",
    "depends": ["mail"],
    "data": ["views/mail_alias_views.xml"],
}
