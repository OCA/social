# Copyright 2024 NSI-SA (<http://nsi-sa.be>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail optional follower notification - Account",
    "summary": "Choose to notify followers for account app",
    "author": "NSI-SA," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "category": "Social Network",
    "version": "17.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["mail_optional_follower_notification", "account"],
    "data": ["wizard/account_move_send_views.xml"],
}
