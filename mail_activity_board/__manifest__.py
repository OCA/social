# Copyright 2018 SDi - David Juaneda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
{
    'name': 'Activities board',
    'version': '11.0.1.0.1',
    'category': 'Social Network',
    'author': 'David Juaneda, '
              'Javier Garcia, '
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/social',
    'summary': 'Add Activity Boards',
    'license': 'GPL-3',
    'depends': [
        'crm','mail','board',
    ],
    'data': [
        'views/activities_boards_views.xml',
        'views/inherit_crm_opportunities_views.xml',
    ],
    'qweb': [],
    'demo': [],
    'installable': True,
}
