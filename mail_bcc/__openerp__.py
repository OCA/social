# -*- coding: utf-8 -*-
##############################################################################
#
#    mail_bcc module for odoo v9
#    Copyright (C) 2015 Anubía, soluciones en la nube,SL (http://www.anubia.es)
#    @author: Juan Formoso <jfv@anubia.es>,
#    @author: Tom Palan <thomas@palan.at>,
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
    'name': 'Mail BCC',
    'summary': 'Blind Carbon Copy available on mails',
    'description': """
Adds a BCC field to mail templates and uses them to send a separate
 copy of the mail to the BCC recipient.
""",
    'version': '0.1',
    'license': 'AGPL-3',
    'author': 'Juan Formoso <jfv@anubia.es>, Tom Palan <thomas@palan.at>',
    'website': 'http://www.anubia.es',
    'category': 'Mail',
    'depends': [
        'mail',
    ],
    'data': [
        'views/views.xml'
    ],
    'demo': [],
    'test': [],
    'installable': True,
}
