# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Message Reply",
    "summary": """
        Make a reply using a message""",
    "version": "14.0.1.0.1",
    "license": "AGPL-3",
    "author": "Creu Blanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mail"],
    "qweb": ["static/src/xml/mail_message_reply.xml"],
    "data": [
        "templates/assets.xml",
        "data/reply_template.xml",
    ],
}
