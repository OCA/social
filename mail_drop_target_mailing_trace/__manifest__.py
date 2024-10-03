# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Mail Drop Target Mailing Trace",
    "version": "16.0.1.0.0",
    "development_status": "Alpha",
    "summary": "Glue module to set access for mailing trace",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "category": "Marketing",
    "license": "AGPL-3",
    "depends": ["mail_drop_target", "mass_mailing"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": True,
    "auto_install": True,
}
