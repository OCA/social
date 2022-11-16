# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail optional autofollow",
    "summary": """
        Choose if you want to automatically add new recipients as followers
        on mail.compose.message""",
    "author": "ACSONE SA/NV," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "category": "Social Network",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["mail"],
    "data": ["wizard/mail_compose_message_view.xml"],
    "installable": True,
}
