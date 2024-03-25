# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Restrict mail templates by default (mass mailing)",
    "summary": "Remove mass mailing user group from default user",
    "version": "16.0.1.0.0",
    "development_status": "Beta",
    "category": "Technical",
    "website": "https://github.com/OCA/social",
    "author": "Hunki Enterprises BV, Odoo Community Association (OCA)",
    "maintainers": ["hbrunn"],
    "license": "AGPL-3",
    "post_init_hook": "post_init_hook",
    "depends": ["mass_mailing", "mail_template_restrict_by_default"],
}
