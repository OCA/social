# © 2022 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Activity on Fetchmail with Team Activity",
    "version": "15.0.1.0.0",
    "development_status": "Alpha",
    "category": "Hidden",
    "author": "initOS GmbH, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "summary": """
    * Uses mail.activity.team to configure automatic activities when mails
     arrive for the specified models.
    * The configuration to add RMA and PO models
     (Settings --> Technical --> Activity Teams menu)
     """,
    "depends": [
        "mail_activity_team",
    ],
    "installable": True,
}
