# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Preview audio files",
    "summary": "Allow to preview audio files",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "author": "Creu Blanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mail_preview_base"],
    "data": [],
    "qweb": ["static/src/xml/preview.xml"],
    "assets": {
        "web.assets_backend": ["mail_preview_audio/static/src/js/*.js"],
        "web.assets_qweb": ["mail_preview_audio/static/src/xml/*.xml"],
    },
}
