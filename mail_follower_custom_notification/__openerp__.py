# -*- coding: utf-8 -*-
# © 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Custom notification settings for followers",
    "version": "8.0.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Social Network",
    "summary": "Let followers choose if they want to receive email "
    "notifications for a given subscription",
    "depends": [
        'mail',
    ],
    "data": [
        "wizards/mail_subtype_assign_custom_notifications.xml",
        "views/mail_message_subtype.xml",
        'views/templates.xml',
    ],
    "qweb": [
        'static/src/xml/mail_follower_custom_notification.xml',
    ],
    "images": [
        'images/mail_follower_custom_notification.png',
    ],
    "installable": True,
}
