# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Mail Activity Partner',
    'summary': 'Add Partner to Activities',
    'version': '12.0.1.0.0',
    'development_status': 'Beta',
    'category': 'Social Network',
    'website': 'https://github.com/OCA/social',
    'author': 'Eficent, Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'installable': True,
    'data': [
        'views/mail_activity_views.xml',
    ],
    'depends': [
        'mail_activity_board',

    ],
}
