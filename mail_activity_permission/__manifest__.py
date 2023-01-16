# Copyright 2023 Hunki Enterprises BV (https://hunki-enterprises.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Permission from activity",
    "summary": "Make records accessible by assigning activities",
    "version": "13.0.1.0.0",
    "development_status": "Alpha",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "Hunki Enterprises BV, Odoo Community Association (OCA)",
    "maintainers": ["hbrunn"],
    "license": "AGPL-3",
    "depends": ["mail"],
    "data": ["views/mail_activity_type.xml", "wizards/mail_activity_bulk_assign.xml"],
    "qweb": ["static/src/xml/mail_activity_permission.xml"],
}
