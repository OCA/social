# Copyright 2019 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestMailOptionalFollowernotifications(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_obj = cls.env["res.partner"]
        cls.partner_01 = cls.env.ref("base.res_partner_2")
        demo_user = cls.env.ref("base.user_demo")
        cls.partner_follower = demo_user.partner_id
        cls.partner_no_follower = demo_user.copy().partner_id
        cls.partner_01.message_subscribe(partner_ids=[cls.partner_follower.id])
        ctx = cls.env.context.copy()
        ctx.update(
            {
                "default_model": "res.partner",
                "default_res_id": cls.partner_01.id,
                "default_composition_mode": "comment",
            }
        )
        cls.mail_compose_context = ctx
        cls.MailCompose = cls.env["mail.compose.message"]

    def _send_mail(self, recipients, notify_followers):
        old_messages = self.env["mail.message"].search([])
        values = self.MailCompose.with_context(
            **self.mail_compose_context
        )._onchange_template_id(False, "comment", "res.partner", self.partner_01.id)[
            "value"
        ]
        values["partner_ids"] = [(6, 0, recipients.ids)]
        values["notify_followers"] = notify_followers
        composer = self.MailCompose.with_context(**self.mail_compose_context).create(
            values
        )
        composer.action_send_mail()
        return self.env["mail.message"].search([]) - old_messages

    def test_1(self):
        """
        Data:
            One partner follower of partner_01
        Test case:
            Send message to the follower and a non follower partner
        Expected result:
            Both are notified
        """
        message = self._send_mail(
            self.partner_follower + self.partner_no_follower, notify_followers=True
        )
        self.assertEqual(
            message.notification_ids.mapped("res_partner_id"),
            self.partner_no_follower + self.partner_follower,
        )

    def test_2(self):
        """
        Data:
            One partner follower of partner_01
        Test case:
            Send message to the non follower partner
        Expected result:
            Both are notified
        """
        message = self._send_mail(self.partner_no_follower, notify_followers=True)
        self.assertEqual(
            message.notification_ids.mapped("res_partner_id"),
            self.partner_no_follower + self.partner_follower,
        )

    def test_3(self):
        """
        Data:
            One partner follower of partner_01
        Test case:
            Send message to the non follower partner and disable the
            notification to followers
        Expected result:
            Only the non follower partner is notified
        """
        message = self._send_mail(self.partner_no_follower, notify_followers=False)
        self.assertEqual(
            message.notification_ids.mapped("res_partner_id"), self.partner_no_follower
        )
