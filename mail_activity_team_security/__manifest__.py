# Copyright 2022 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Activity Team Security",
    "summary": "Control who can perform actions on activities based on teams",
    "version": "15.0.1.0.0",
    "development_status": "Alpha",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "maintainers": ["ivantodorovich"],
    "license": "AGPL-3",
    "category": "Marketing",
    "website": "https://github.com/OCA/social",
    "depends": ["mail_activity_security", "mail_activity_team"],
    "auto_install": True,
    "data": ["views/mail_activity_type.xml"],
}
