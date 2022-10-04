# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Message Reply",
    "summary": """
        Make a reply using a message""",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "author": "Creu Blanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mail"],
    "data": [],
    "assets": {
        "web.assets_qweb": [
            "/mail_quoted_reply/static/src/xml/mail_message_reply.xml",
        ],
        "web.assets_backend": [
            "/mail_quoted_reply/static/src/models/mail_message_reply.esm.js",
            "/mail_quoted_reply/static/src/components/mail_message_reply.esm.js",
        ],
    },
}
