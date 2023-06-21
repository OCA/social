# Copyright 2020 Creu Blanca
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Mail Preview",
    "summary": """
        Base to add more previewing options""",
    "version": "16.0.1.0.0",
    "license": "LGPL-3",
    "author": "Creu Blanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mail"],
    "data": [
        "views/ir_attachment_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_preview_base/static/src/xml/preview.xml",
            "mail_preview_base/static/src/js/preview.esm.js",
            "mail_preview_base/static/src/scss/preview.scss",
        ],
    },
}
