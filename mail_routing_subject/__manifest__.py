# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Match mails by subject",
    "summary": "Fall back to matching by subject for incoming emails",
    "version": "14.0.1.0.0",
    "development_status": "Alpha",
    "category": "Productivity/Discuss",
    "website": "https://github.com/OCA/social",
    "author": "Hunki Enterprises BV, Odoo Community Association (OCA)",
    "maintainers": ["hbrunn"],
    "license": "AGPL-3",
    "depends": [
        "mail",
    ],
    "data": [
        "data/ir_config_parameter.xml",
        "views/res_config_settings.xml",
    ],
}
