# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail Sender Company Aware",
    "summary": "Send emails with company specific mail domain",
    "version": "14.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": ("Therp BV, " "Odoo Community Association (OCA)"),
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
        "mail_outbound_static",  # Need the domain whitelist on outgoing server.
    ],
    "data": [
        "views/res_company_view.xml",
        "views/res_partner_view.xml",
    ],
}
