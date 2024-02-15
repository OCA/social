# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Email Template Configurator",
    "summary": """
        Simplifies use of placeholders in email templates""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": [
        "mail",
    ],
    "data": [
        "security/groups.xml",
        "security/email_template_placeholder.xml",
        "views/email_template_placeholder.xml",
        "views/mail_template.xml",
    ],
    "installable": True,
}
