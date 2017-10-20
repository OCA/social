# -*- coding: utf-8 -*-
# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': "Mail optional follower notification",

    'summary': """
        Choose if you want to automatically notify followers
        on mail.compose.message""",
    'author': 'ACSONE SA/NV,'
              'Odoo Community Association (OCA)',
    'website': "http://acsone.eu",
    'category': 'Social Network',
    'version': '10.0.1.0.1',
    'license': 'AGPL-3',
    'depends': [
        'mail',
    ],
    'data': [
        'wizard/mail_compose_message_view.xml',
    ],
}
