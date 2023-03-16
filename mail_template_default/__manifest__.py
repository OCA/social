# Copyright 2023 Solvti sp. z o.o. (https://solvti.pl)

{
    "name": "Mail Template Default",
    "summary": "Create rules to apply default mail template in composer",
    "version": "15.0.1.0.0",
    "category": "Social Network",
    "author": "Solvti, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["mail"],
    "website": "https://github.com/OCA/social",
    "data": [
        "security/ir.model.access.csv",
        "views/mail_template_rule_views.xml",
    ],
}
