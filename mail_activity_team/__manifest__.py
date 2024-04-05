# Copyright 2018-22 ForgeFlow S.L.
# Copyright 2021 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Activity Team",
    "summary": "Add Teams to Activities",
    "version": "17.0.1.0.0",
    "development_status": "Alpha",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "ForgeFlow, Sodexis, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail_activity_board"],
    "data": [
        "security/ir.model.access.csv",
        "security/mail_activity_team_security.xml",
        "views/ir_actions_server_views.xml",
        "views/mail_activity_type.xml",
        "views/mail_activity_team_views.xml",
        "views/mail_activity_views.xml",
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_activity_team/static/src/components/*/*",
            "mail_activity_team/static/src/models/*",
        ],
    },
}
