# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import odoo.tests.common as common


class TestMailNotification(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.sender = self.env['res.partner'].create({
            'name': 'Test sender',
            'email': 'sender@example.com',
        })
        self.recipient = self.env['res.partner'].create({
            'name': 'Test recipient',
            'email': 'recipient@example.com',
        })
        self.message = self.env['mail.message'].create({
            'subject': 'Message test',
            'author_id': self.sender.id,
            'email_from': self.sender.email,
            'message_type': 'comment',
            'model': 'res.partner',
            'res_id': self.recipient.id,
            'partner_ids': [(4, self.recipient.id)],
            'body': '<p>This is a test message</p>',
        })

        self.record = self.recipient

        self.rdata = [{
            'type': 'customer',
            'id': self.recipient.id,
            'groups': [None],
            'active': True,
            'share': True,
            'notif': 'email'
        }]
        self.force_send = True
        self.send_after_commit = True
        self.model_description = False
        self.mail_auto_delete = True

    def test_get_signature_header(self):
        rep = self.recipient._notify(
            self.message,
            self.rdata,
            self.record,
            self.force_send,
            self.send_after_commit,
            self.model_description,
            self.mail_auto_delete,
        )

        self.assertTrue(rep, "message not send")
        self.assertTrue(
            self.recipient.name in self.message.body,
            "Partner name is not in the body of the mail",
        )
