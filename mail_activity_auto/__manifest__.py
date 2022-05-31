# Copyright 2016-22 PESOL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Activity Auto",
    "summary": "Add automatization to Activities",
    "version": "15.0.1.0.0",
    "development_status": "Alpha",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "PESOL, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["queue_job"],
    "data": [
        "security/ir.model.access.csv",
        "views/mail_activity_views.xml",
        "views/mail_activity_type_views.xml",
        "views/mail_activity_type_action_views.xml",
    ],
}
