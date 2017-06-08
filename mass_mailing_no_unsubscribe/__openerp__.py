# -*- coding: utf-8 -*-
# © 2015 ONESTEiN BV (<http://www.onestein.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Mass mailing unsubscription',
    'images': ['static/description/main_screenshot.png'],
    'summary': """Configurable unsubscribe possibility for mass mailing""",
    'version': '8.0.1.0.0',
    'author': 'ONESTEiN BV,Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'website': 'http://onestein.eu',
    'category': 'Marketing',
    'depends': [
        'mass_mailing'
    ],
    'data': [
        'views/mail_mass_mailing.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
