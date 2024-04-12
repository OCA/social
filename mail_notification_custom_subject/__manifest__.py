# Copyright 2020-2021 Tecnativa - João Marques
# Copyright 2021 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail Notification Custom Subject",
    "summary": "Apply a custom subject to mail notifications",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/mail_notification_custom_subject_views.xml",
    ],
    "development_status": "Production/Stable",
    "maintainers": ["yajo"],
}
