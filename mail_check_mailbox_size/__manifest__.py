# Copyright 2018 Lorenzo Battistini
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Check mailbox size",
    "summary": "Send an email summarizing the current space used by a mailbox",
    "version": "12.0.1.0.0",
    "development_status": "Beta",
    "website": "https://github.com/OCA/social",
    "author": "Agile Business Group, Odoo Community Association (OCA)",
    "maintainers": ["eLBati"],
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "fetchmail",
    ],
    "data": [
        "views/fetchmail_view.xml",
        "data/cron_data.xml",
    ],
}
