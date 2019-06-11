# Copyright 2018 Eficent <http://www.eficent.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    "name": "Mail Activity Done",
    "version": "12.0.2.0.0",
    "author": "Eficent,"
              "Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "category": "Discuss",
    "depends": [
        'mail',
    ],
    "data": [
        'views/templates.xml',
        'views/mail_activity_views.xml',
    ],
    "pre_init_hook": "pre_init_hook",
    "post_load": "post_load_hook",
    'uninstall_hook': 'uninstall_hook',
}
