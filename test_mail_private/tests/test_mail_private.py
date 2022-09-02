# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
from odoo.tools import formataddr
from odoo.addons.test_mail.tests.common import Moderation
from odoo.tests.common import post_install, at_install
from lxml import etree


@at_install(False)
@post_install(True)
class TestMailPrivate(Moderation):

    @classmethod
    def setUpClass(cls):
        super(TestMailPrivate, cls).setUpClass()
        self = cls

        param = self.env['ir.config_parameter'].search([
            ('key', '=', 'mail_restrict_follower_selection.domain')
        ])
        if param:
            self.env['ir.config_parameter'].set_param(
                'mail_restrict_follower_selection.domain.res.partner',
                '[]'
            )
        self.user_01 = self.env['res.users'].create({
            'name': 'user_01',
            'login': 'demo_user_01',
            'email': 'demo@demo.de',
            'notification_type': 'inbox',
        })
        self.user_02 = self.env['res.users'].create({
            'name': 'user_02',
            'login': 'demo_user_02',
            'email': 'demo2@demo.de',
            'notification_type': 'inbox',
        })
        self.user_03 = self.env['res.users'].create({
            'name': 'user_03',
            'login': 'demo_user_03',
            'email': 'demo3@demo.de',
            'notification_type': 'inbox',
        })
        self.partner = self.env['res.partner'].create({
            'name': 'Partner',
            'customer': True,
            'email': 'test@test.com',
        })
        self.group_1 = self.env['res.groups'].create({
            'name': 'DEMO GROUP 1',
            'users': [(4, self.user_01.id)],
        })
        self.group_2 = self.env['res.groups'].create({
            'name': 'DEMO GROUP 2',
            'users': [(4, self.user_02.id)],
        })
        self.message_group_1 = self.env['mail.security.group'].create({
            'name': 'GROUP 1',
            'model_ids': [(4, self.env.ref('base.model_res_partner').id)],
            'group_ids': [(4, self.group_1.id)],
        })
        self.message_group_2 = self.env['mail.security.group'].create({
            'name': 'GROUP 2',
            'model_ids': [(4, self.env.ref('base.model_res_partner').id)],
            'group_ids': [(4, self.group_2.id)],
        })
        self.subtypes, _, _, _, _ = self.env[
            'mail.message.subtype'
        ]._get_auto_subscription_subtypes(self.partner._name)
        self.partner.message_subscribe(
            partner_ids=self.user_01.partner_id.ids,
            subtype_ids=self.subtypes,
        )
        self.partner.message_subscribe(
            partner_ids=self.user_02.partner_id.ids,
            subtype_ids=self.subtypes,
        )
        self.partner.message_subscribe(
            partner_ids=self.user_03.partner_id.ids,
            subtype_ids=self.subtypes,
        )

    def _get_notifications(self, message, user):
        return self.env['mail.notification'].search([
            ('mail_message_id', '=', message.id),
            ('res_partner_id', '=', user.partner_id.id),
            ('is_read', '=', False),
        ])

    def test_normal_usage(self):
        # pylint: disable = C8107
        message = self.partner.message_post(body="DEMO_01")
        self.assertTrue(
            self._get_notifications(message, self.user_01)
        )
        self.assertTrue(
            self._get_notifications(message, self.user_02)
        )
        self.assertTrue(
            self._get_notifications(message, self.user_03)
        )

    def test_private_usage(self):
        # pylint: disable = C8107
        message = self.partner.sudo(self.user_01.id).with_context(
            default_mail_group_id=self.message_group_1.id
        ).message_post(body="DEMO_01")
        self.assertFalse(
            self._get_notifications(message, self.user_02)
        )
        self.assertFalse(
            self.env['mail.message'].sudo(self.user_02.id).search([
                ('id', '=', message.id)
            ])
        )
        self.assertFalse(
            self._get_notifications(message, self.user_03)
        )

    def test_private_message_data(self):
        # pylint: disable = C8107
        message = self.partner.with_context(
            default_mail_group_id=self.message_group_1.id
        ).message_post(body="DEMO_01")
        self.assertTrue(message.message_format()[0]['private'])

    def test_message_data(self):
        # pylint: disable = C8107
        message = self.partner.message_post(body="DEMO_01")
        self.assertFalse(message.message_format()[0]['private'])

    def test_private_notification(self):
        # pylint: disable = C8107
        message = self.partner.with_context(
            default_mail_group_id=self.message_group_1.id
        ).message_post(body="DEMO_01")
        self.assertTrue(
            self._get_notifications(message, self.user_01)
        )
        self.assertEqual(
            self.env['mail.message'].sudo(self.user_01.id).search([
                ('id', '=', message.id)
            ]), message
        )
        self.assertFalse(
            self._get_notifications(message, self.user_02)
        )
        self.assertFalse(
            self.env['mail.message'].sudo(self.user_02.id).search([
                ('id', '=', message.id)
            ])
        )
        self.assertFalse(
            self._get_notifications(message, self.user_03)
        )

    def test_attachment(self):
        attachment = self.env['ir.attachment'].sudo(self.user_01.id).create({
            'datas': base64.b64encode("TXT DATA".encode("utf-8")),
            'name': 'demo_file.txt',
            'res_model': 'mail.compose.message',
        })
        # pylint: disable = C8107
        message = self.partner.sudo(self.user_01.id).message_post(
            body="DEMO_01", attachment_ids=attachment.ids)
        self.assertFalse(attachment.mail_group_id)
        self.assertFalse(message.mail_group_id)
        self.assertIn(attachment, message.attachment_ids)

    def test_attachment_private(self):
        attachment = self.env['ir.attachment'].sudo(self.user_01.id).create({
            'datas': base64.b64encode("TXT DATA".encode("utf-8")),
            'name': 'demo_file.txt',
            'res_model': 'mail.compose.message',
        })
        # pylint: disable = C8107
        message = self.partner.sudo(self.user_01.id).with_context(
            default_mail_group_id=self.message_group_1.id
        ).message_post(body="DEMO_01", attachment_ids=attachment.ids)
        self.assertEqual(self.message_group_1, attachment.mail_group_id)
        self.assertEqual(self.message_group_1, message.mail_group_id)
        self.assertIn(attachment, message.attachment_ids)

    def test_allow_private(self):
        self.assertTrue(
            self.partner.sudo(self.user_01.id).allow_private
        )
        self.assertTrue(
            self.partner.sudo(self.user_02.id).allow_private
        )
        view = self.partner.fields_view_get(view_type="form")
        view_element = etree.XML(view['arch'])
        self.assertTrue(view_element.xpath("//field[@name='allow_private']"))

    def test_compose_message_private(self):
        current_messages = self.partner.message_ids
        compose = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': self.partner._name,
            'default_res_id': self.partner.id
        }).sudo(self.user_01).create({
            'subject': 'Subject',
            'body': 'Body text',
            'partner_ids': []})
        self.assertTrue(compose.allow_private)
        compose.mail_group_id = self.message_group_1
        compose.send_mail()
        message = self.partner.message_ids - current_messages
        self.assertTrue(message)
        self.assertEqual(message.mail_group_id, self.message_group_1)

    def test_compose_message_public(self):
        current_messages = self.partner.message_ids
        compose = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': self.partner._name,
            'default_res_id': self.partner.id
        }).sudo(self.user_01).create({
            'subject': 'Subject',
            'body': 'Body text',
            'partner_ids': []})
        self.assertTrue(compose.allow_private)
        compose.send_mail()
        message = self.partner.message_ids - current_messages
        self.assertTrue(message)
        self.assertFalse(message.mail_group_id)

    def test_compose_message_compute(self):
        compose = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': self.partner._name,
            'default_res_id': self.partner.id
        }).sudo(self.user_01.id).create({
            'subject': 'Subject',
            'body': 'Body text',
            'partner_ids': []})
        self.assertTrue(compose.allow_private)
        compose = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': self.partner._name,
            'default_res_id': self.partner.id
        }).sudo(self.user_03.id).create({
            'subject': 'Subject',
            'body': 'Body text',
            'partner_ids': []})
        self.assertFalse(compose.allow_private)

    def test_compose_message_compute_no_field(self):
        """
        Compose Wizard does not allow private
        if related record has no field `allow_private`.
        """
        mail_message = self.env['mail.message'].search([], limit=1)
        self.assertTrue(mail_message)
        self.assertFalse(hasattr(mail_message, 'allow_private'))

        compose = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': mail_message._name,
            'default_res_id': mail_message.id
        }).sudo(self.user_01.id).create({
            'subject': 'Subject',
            'body': 'Body text',
            'partner_ids': []})
        self.assertFalse(compose.allow_private)

    def test_security_groups(self):
        groups = self.partner.sudo(
            self.user_01.id).get_message_security_groups()
        self.assertTrue(groups)
        self.assertEqual(1, len(groups))
        self.assertEqual(groups[0]['id'], self.message_group_1.id)
        groups = self.partner.sudo(
            self.user_02.id).get_message_security_groups()
        self.assertTrue(groups)
        self.assertEqual(1, len(groups))
        self.assertEqual(groups[0]['id'], self.message_group_2.id)
        groups = self.partner.sudo(
            self.user_03.id).get_message_security_groups()
        self.assertFalse(groups)

    def test_email_sending(self):
        self.assertFalse(self._mails)
        self.user_01.write({'notification_type': 'email'})
        self.user_02.write({'notification_type': 'email'})
        # pylint: disable = C8107
        message = self.partner.with_context(
            default_mail_group_id=self.message_group_1.id
        ).message_post(body="DEMO_01")
        self.assertTrue(message.mail_group_id)
        self.assertFalse(self._get_notifications(message, self.user_01))
        self.assertFalse(self.env['mail.mail'].search([
            ('mail_message_id', '=', message.id)
        ]))
        self.assertTrue(self._mails)
        self.assertEqual(2, len(self._mails))
        partner = self.user_01.partner_id
        email_to = [
            formataddr((partner.name or 'False', partner.email or 'False'))
        ]
        self.assertEqual(
            self._mails[0]['email_to'],
            email_to)
        self.assertFalse(
            self._get_notifications(message, self.user_02)
        )
        self.assertFalse(
            self._get_notifications(message, self.user_03)
        )
