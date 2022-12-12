# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Autosubscribe",
    "summary": "Automatically subscribe partners to its company's business documents",
    "version": "14.0.1.0.0",
    "author": "Camptocamp SA, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Marketing",
    "depends": ["mail"],
    "website": "https://github.com/OCA/social",
    "data": [
        "security/ir.model.access.csv",
        "views/mail_autosubscribe.xml",
        "views/mail_template.xml",
        "views/res_partner.xml",
    ],
}
