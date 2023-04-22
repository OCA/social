# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail Activity Reminder",
    "version": "13.0.1.0.0",
    "category": "Discuss",
    "website": "https://github.com/OCA/social",
    "author": "CorporateHub, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "summary": "Reminder notifications about planned activities",
    "depends": ["mail"],
    "data": [
        "data/mail_activity_reminder_cron.xml",
        "views/mail_activity_type.xml",
        "data/mail_activity_template.xml",
    ],
}
