# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Mail Activity Team',
    'summary': 'Add Teams to Activities',
    'version': '12.0.1.2.0',
    'development_status': 'Beta',
    'category': 'Social Network',
    'website': 'https://github.com/OCA/social',
    'author': 'Eficent, Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'installable': True,
    'depends': [
        'mail_activity_board',
    ],
    'data': [
        'views/calendar_event.xml',
        'views/assets_backend.xml',
        'security/ir.model.access.csv',
        'security/mail_activity_team_security.xml',
        'views/mail_activity_team_views.xml',
        'views/mail_activity_views.xml',
        'views/res_users_views.xml',
    ],

    'qweb': [
        'static/src/xml/systray.xml',
    ],
}
