##############################################################################
#
#     This file is part of mail_attach_existing_attachment,
#     an Odoo module.
#
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     mail_attach_existing_attachment is free software:
#     you can redistribute it and/or modify it under the terms of the GNU
#     Affero General Public License as published by the Free Software
#     Foundation,either version 3 of the License, or (at your option) any
#     later version.
#
#     mail_attach_existing_attachment is distributed
#     in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
#     even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#     PURPOSE.  See the GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with mail_attach_existing_attachment.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': "Mail Attach Existing Attachment",
    'summary': "Adding attachment on the object by sending this one",
    'author': "ACSONE SA/NV, "
              "Tecnativa, "
              "Odoo Community Association (OCA)",
    'website': "https://github.com/OCA/social",
    'category': 'Social Network',
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'depends': [
        'mail',
        'document',
    ],
    'data': [
        'wizard/mail_compose_message_view.xml',
    ],
    'installable': True,
}
