{
    "name": "Mail Activity Redirection",
    "summary": "Redirect activities to specific users",
    "version": "12.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "DEC, Odoo Community Association (OCA)",
    "maintainers": ["ypapouin"],
    "license": "AGPL-3",
    "depends": ["mail", ],
    "data":
        [
            "security/ir.model.access.csv",
            "data/mail_activity_redirection.xml",
            "views/mail_activity_redirection.xml",
            "views/res_config_settings.xml",
        ],
    "installable": True
}
