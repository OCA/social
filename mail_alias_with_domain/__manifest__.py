# Copyright 2023 Solvti sp. z o.o. (https://solvti.pl)

{
    "name": "Mail Alias With Domain",
    "summary": """
        Extend alias fnctionality by giving possibility
        to setup alias with custom domain""",
    "author": "Solvti, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "version": "13.0.1.0.0",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["mail"],
    "data": ["views/mail_alias_views.xml"],
}
