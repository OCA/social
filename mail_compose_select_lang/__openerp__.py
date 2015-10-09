# -*- coding: utf-8 -*-
##############################################################################
# (c) 2015 Pedro M. Baeza
# License AGPL-3 - See LICENSE file on root folder for details
##############################################################################

{
    'name': 'Select language in mail compose window',
    'version': '8.0.1.0.0',
    'category': 'Marketing',
    'author': 'Serv. Tecnol. Avanzados - Pedro M. Baeza, '
              'Antiun Ingeniería S.L.,'
              'Odoo Community Association (OCA)',
    'website': 'http://www.serviciosbaeza.com',
    'depends': [
        'email_template',
    ],
    'data': [
        'wizard/mail_compose_message_view.xml',
    ],
    "installable": True,
}
