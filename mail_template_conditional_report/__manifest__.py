# Copyright 2025 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail template conditional report",
    "summary": "Add a domain to print dynamic attachments on mail template",
    "version": "18.0.1.0.0",
    "category": "Mail",
    "website": "https://github.com/OCA/social",
    "author": "ACSONE SA/NV, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "data": [
        "views/mail_template.xml",
        "security/mail_template_report.xml",
    ],
    "demo": [
        "demo/ir_actions_report.xml",
        "demo/mail_template.xml",
    ],
    "pre_init_hook": "_pre_init_hook",
}
