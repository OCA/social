# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail Discuss Channel Unread Sort",
    "summary": "Sort discuss channels by most recent unread activity",
    "version": "17.0.1.0.0",
    "category": "Discuss",
    "author": "APSL-Nagarro, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "mail_discuss_channel_unread_sort/static/src/js/discuss_app_category_model_patch.esm.js",
        ],
    },
    "installable": True,
}
