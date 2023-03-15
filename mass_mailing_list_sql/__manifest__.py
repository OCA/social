# Copyright (C) 2023 ForgeFlow, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Mass Mailing List SQL",
    "category": "Marketing",
    "summary": "Mass mailing lists that get autopopulated, rules defined in SQL",
    "version": "14.0.1.0.0",
    "author": "ForgeFlow S.L., Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mass_mailing_list_dynamic", "sql_request_abstract"],
    "data": ["views/mailing_list_views.xml"],
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
