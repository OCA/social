# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Broker",
    "summary": """
        Set a broker""",
    "version": "13.0.1.0.0",
    "license": "AGPL-3",
    "author": "Creu Blanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "qweb": ["static/src/xml/broker.xml"],
    "depends": ["mail", "base_rest"],
    "pre_init_hook": "pre_init_hook",
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/mail_broker.xml",
        "templates/assets.xml",
        "views/mail_broker_channel.xml",
    ],
}
