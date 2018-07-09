# Copyright 2016 David Juaneda - <djuaneda@sdi.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Activities board',
    'summary': 'Add Activity Boards',
    'version': '11.0.1.0.0',
    'development_status': 'Beta',
    'category': 'Uncategorized',
    'website': 'https://github.com/OCA/social',
    'author': 'SDi, David Juaneda, Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'calendar',
        'board',
    ],
    'data': [
        'views/templates.xml',
        'views/mail_activity_view.xml',
    ],
    'qweb': [
        'static/src/xml/inherit_chatter.xml',
    ]
}
