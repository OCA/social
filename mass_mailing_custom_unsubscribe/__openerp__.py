# -*- coding: utf-8 -*-
# Python source code encoding : https://www.python.org/dev/peps/pep-0263/
##############################################################################
#
#    OpenERP, Odoo Source Management Solution
#    Copyright (c) 2015 Antiun Ingeniería S.L. (http://www.antiun.com)
#                       Antonio Espinosa <antonioea@antiun.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': "Customizable unsubscription process on mass mailing emails",
    'category': 'Marketing',
    'version': '8.0.2.1.0',
    'depends': [
        'mass_mailing',
        'website_crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/install_salt.xml',
        'data/mail_unsubscription_reason.xml',
        'views/assets.xml',
        'views/mail_unsubscription_reason_view.xml',
        'views/mail_mass_mailing_list_view.xml',
        'views/mail_unsubscription_view.xml',
        'views/pages.xml',
    ],
    'images': [
        'images/failure.png',
        'images/form.png',
        'images/success.png',
    ],
    'author': 'Antiun Ingeniería S.L., '
              'Tecnativa,'
              'Odoo Community Association (OCA)',
    'website': 'http://www.antiun.com',
    'license': 'AGPL-3',
    'installable': True,
}
