# -*- coding: utf-8 -*-
# Copyright 2026 nurefexc (https://nurefexc.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
{
    'name': 'ntfy.sh Push Notifications',
    'version': '17.0.1.0.0',
    'summary': 'Asynchronous push notifications via ntfy.sh protocol',
    'author': 'nurefexc',
    'website': 'https://nurefexc.com',
    'category': 'Technical/Communication',
    'depends': ['mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/res_users_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
