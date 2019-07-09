# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Email Template Multi Report',
    'version': '11.0.1.0.0',
    'category': 'Uncategorized',
    'summary': 'Multiple Reports in Email Templates',
    'author': 'Savoir-faire Linux, '
              'Bloopark systems GmbH & Co. KG, '
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/social',
    'license': 'AGPL-3',
    'depends': [
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mail_template.xml',
    ],
    'installable': True,
}
