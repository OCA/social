# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail History Mark as Unread",
    "summary": "Add 'Mark as Unread' action to messages in History mailbox",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "mail_history_mark_unread/static/src/message_actions_patch.esm.js",
            "mail_history_mark_unread/static/src/message_service_patch.esm.js",
            "mail_history_mark_unread/static/src/mail_core_web_service_patch.esm.js",
        ],
    },
}
