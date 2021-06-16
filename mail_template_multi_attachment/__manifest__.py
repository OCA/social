# Copyright 2021 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail template multi attachment",
    "summary": """Module who allows to generate multi attachments on
    an email template.""",
    "version": "13.0.1.0.0",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mail"],
    "data": [
        "security/mail_template_report.xml",
        "views/mail_template_report.xml",
        "views/mail_template.xml",
    ],
}
