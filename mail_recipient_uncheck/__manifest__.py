# Copyright 2019 Trobz <https://trobz.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Mail Recipient Uncheck',
    'summary': """
        Uncheck recipients suggestions when sending a message""",
    'version': '12.0.1.0.0',
    'development_status': 'Mature',
    'license': 'AGPL-3',
    'author': 'Trobz,Odoo Community Association (OCA)',
    'maintainers': ['nilshamerlinck'],
    'category': 'Social Network',
    'website': 'https://github.com/OCA/social',
    'depends': [
        'mail'
    ],
    'data': [
        'views/mail_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
