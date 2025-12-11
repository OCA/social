# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Chatter Split",
    "summary": "Separate user messages, activities and automatic logs in the chatter",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "mail_chatter_split/static/src/chatter_patch.esm.js",
            "mail_chatter_split/static/src/chatter_patch.xml",
            "mail_chatter_split/static/src/activity_list_patch.xml",
            "mail_chatter_split/static/src/chatter.scss",
            "mail_chatter_split/static/src/thread_model_patch.esm.js",
            "mail_chatter_split/static/src/thread_patch.esm.js",
            "mail_chatter_split/static/src/thread_patch.xml",
        ],
        "web.assets_web_dark": [
            "mail_chatter_split/static/src/chatter.dark.scss",
        ],
    },
}
