# Copyright 2023 ForgeFlow S. L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Mail Thread Subject Ignore",
    "version": "15.0.1.0.0",
    "license": "LGPL-3",
    "category": "Mail",
    "summary": """Ignore Mails with Subject""",
    "website": "https://github.com/OCA/social",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "depends": ["fetchmail"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_thread_subject_ignore.xml",
        "views/mail_thread_subject_ignore_view.xml",
    ],
    "installable": True,
}
