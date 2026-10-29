# SPDX-FileCopyrightText: 2025 hugues de keyzer
#
# SPDX-License-Identifier: AGPL-3.0-or-later

{
    "name": "Mass Mailing Disable Tracking",
    "summary": "Allow to disable open and link click tracking in mass mailing messages",
    "version": "18.0.1.0.0",
    "category": "Marketing/Email Marketing",
    "website": "https://github.com/OCA/social",
    "author": "hugues de keyzer, Odoo Community Association (OCA)",
    "maintainers": ["huguesdk"],
    "license": "AGPL-3",
    "depends": [
        "mass_mailing",
    ],
    "excludes": [
        "mail_tracking",
    ],
    "data": [
        "views/res_config_settings_view.xml",
    ],
}
