{
    "name": "Chatter Visibility",
    "version": "18.0.1.0.0",
    "summary": """Enable users to control chatter visibility on form views according to
    their privacy preferences""",
    "license": "LGPL-3",
    "author": "BizzAppDev Systems Pvt. Ltd., Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["web"],
    "data": [
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "chatter_visibility/static/src/scss/chatter_visibility.scss",
            "chatter_visibility/static/src/js/form.esm.js",
        ],
    },
    "installable": True,
}
