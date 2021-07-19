# Copyright 2021 Hunki Entperprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Predefined mail activities",
    "summary": "Add predefined mail activities to arbitrary models",
    "version": "13.0.1.0.0",
    "development_status": "Beta",
    "category": "Discuss",
    "website": "https://github.com/OCA/social",
    "author": "Hunki Enterprises BV, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["mail_activity_done"],
    "data": [
        "security/mail_activity_predefined.xml",
        "views/mail_activity_type.xml",
        "views/mail_activity.xml",
    ],
    "demo": ["demo/mail_activity_predefined.xml"],
}
