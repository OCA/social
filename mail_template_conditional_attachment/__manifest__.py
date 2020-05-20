# Copyright 2019 Druidoo - Iván Todorovich <ivan.todorovich@druidoo.io>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Email Template Conditional Attachment",
    "summary": "Allow to add conditional attachments to email templates",
    "version": "12.0.1.0.0",
    "category": "Uncategorized",
    "website": "https://github.com/OCA/social",
    "author": "Druidoo, Odoo Community Association (OCA)",
    "maintainers": [
        "ivantodorovich"
    ],
    "license": "AGPL-3",
    "depends": [
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/mail_template.xml",
    ],
    "demo": [
        "demo/demo.xml",
    ]
}
