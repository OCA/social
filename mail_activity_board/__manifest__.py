# Copyright 2018 David Juaneda - <djuaneda@sdi.es>
# Copyright 2021 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Activity Board",
    "summary": "Add Activity Boards",
    "version": "15.0.2.1.2",
    "development_status": "Beta",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "SDi, David Juaneda, Sodexis, ACSONE SA/NV, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["calendar", "board"],
    "data": ["security/groups.xml", "views/mail_activity_view.xml"],
    "assets": {
        "web.assets_backend": [
            "mail_activity_board/static/src/components/chatter_topbar/chatter_topbar.esm.js",
            "mail_activity_board/static/src/js/systray.esm.js",
        ],
        "web.assets_qweb": [
            "mail_activity_board/static/src/components/chatter_topbar/chatter_topbar.xml",
            "mail_activity_board/static/src/xml/systray.xml",
        ],
    },
}
