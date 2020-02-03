# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Mail Activity Creator',
    'summary': """
        Show activities creator""",
    'version': '11.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Creu Blanca,Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/social',
    'depends': [
        'mail'
    ],
    'data': [
        'views/mail_activity_views.xml',
    ],
    'qweb': [
        'static/src/xml/activity.xml',
    ],
}
