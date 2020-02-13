# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Mail Activity Reminder',
    'version': '12.0.1.0.0',
    'category': 'Discuss',
    'website': 'https://github.com/OCA/social',
    'author':
        'Brainbean Apps, '
        'Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'installable': True,
    'application': False,
    'summary': 'Reminder notifications about planned activities',
    'depends': [
        'mail',
    ],
    'data': [
        'data/mail_activity_reminder_cron.xml',
        'views/mail_activity_type.xml',
    ],
}
