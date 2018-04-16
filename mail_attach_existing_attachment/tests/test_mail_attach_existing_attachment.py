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

from odoo.tests import common


class TestAttachExistingAttachment(common.TransactionCase):

    def setUp(self):
        super(TestAttachExistingAttachment, self).setUp()
        self.partner_obj = self.env['res.partner']
        self.partner_01 = self.env['res.partner'].create({
            'name': 'Partner 1',
            'email': 'partner1@example.org',
            'is_company': True,
            'parent_id': False,
        })

    def test_send_email_attachment(self):
        attach1 = self.env['ir.attachment'].create({
            'name': 'Attach1', 'datas_fname': 'Attach1',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_model': 'res.partner', 'res_id': self.partner_01.id})
        vals = {'model': 'res.partner',
                'partner_ids': [(6, 0, [self.partner_01.id])],
                'res_id': self.partner_01.id,
                'object_attachment_ids': [(6, 0, [attach1.id])]
                }
        mail = self.env['mail.compose.message'].create(vals)
        values = mail.get_mail_values([self.partner_01.id])
        self.assertTrue(attach1.id in
                        values[self.partner_01.id]['attachment_ids'])
