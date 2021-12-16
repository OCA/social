# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Telegram Broker",
    "summary": """
        Set a broker for telegram""",
    "version": "13.0.1.0.0",
    "license": "AGPL-3",
    "author": "Creu Blanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mail_broker"],
    "data": ["views/mail_broker.xml"],
    "external_dependencies": {"python": ["python-telegram-bot", "cairosvg", "lottie"]},
}
