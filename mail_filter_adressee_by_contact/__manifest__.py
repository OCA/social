# Copyright 2021 Akretion (https://www.akretion.com).
# @author Kévin Roche <kevin.roche@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail filter adressee by partner contacts and users",
    "summary": "Adresses filter by partner contacts and users",
    "version": "18.0.1.1.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "Akretion, Odoo Community Association (OCA)",
    "maintainers": ["Kev-Roche"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
        "sale",
    ],
    "data": [
        "views/mail_compose_message_view.xml",
        "views/mail_invoice_send_view.xml",
    ],
}
