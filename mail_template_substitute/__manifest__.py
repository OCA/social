# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Template Substitute",
    "summary": """
        This module allows to create substitution rules for mail templates.
        """,
    "version": "12.0.1.0.1",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV,"
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["base", "mail", "report_substitute"],
    "data": [
        "security/mail_template_substitution_rule.xml",
        "views/mail_template.xml",
    ],
}
