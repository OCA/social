# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail Discuss Channel Hide Sidebar",
    "summary": (
        "Hide subscribed channels from Discuss sidebar " "until a new message arrives"
    ),
    "version": "17.0.1.0.0",
    "category": "Discuss",
    "author": "APSL-Nagarro, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "mail_discuss_channel_hide_sidebar/static/src/core/common/channel_member_model_patch.esm.js",
            "mail_discuss_channel_hide_sidebar/static/src/discuss/core/common/discuss_core_common_service_patch.esm.js",
            "mail_discuss_channel_hide_sidebar/static/src/core/web/discuss_sidebar_categories_patch.esm.js",
            "mail_discuss_channel_hide_sidebar/static/src/core/web/discuss_sidebar_categories_patch.xml",
        ],
    },
    "installable": True,
}
