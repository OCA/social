# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestAttachExistingAttachment(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner_obj = self.env["res.partner"]
        self.partner_01 = self.env.ref("base.res_partner_10")
        self.partner_02 = self.env.ref("base.res_partner_address_17")

    def test_send_email_attachment(self):
        ctx = self.env.context.copy()
        ctx.update(
            {
                "default_model": "res.partner",
                "default_res_ids": self.partner_01.ids,
                "default_composition_mode": "comment",
            }
        )
        mail_compose = self.env["mail.compose.message"]
        values = {
            "partner_ids": [(4, self.partner_02.id)],
            "composition_mode": "comment",
        }
        compose_id = mail_compose.with_context(**ctx).create(values)
        compose_id.autofollow_recipients = False
        compose_id.with_context(**ctx).action_send_mail()
        res = self.env["mail.followers"].search(
            [
                ("res_model", "=", "res.partner"),
                ("res_id", "=", self.partner_01.id),
                ("partner_id", "=", self.partner_02.id),
            ]
        )
        # I check if the recipient isn't a follower
        self.assertEqual(len(res.ids), 0)
        compose_id = mail_compose.with_context(**ctx).create(values)
        compose_id.autofollow_recipients = True
        compose_id.with_context(**ctx).action_send_mail()
        res = self.env["mail.followers"].search(
            [
                ("res_model", "=", "res.partner"),
                ("res_id", "=", self.partner_01.id),
                ("partner_id", "=", self.partner_02.id),
            ]
        )
        # I check if the recipient is a follower
        self.assertEqual(len(res.ids), 1)
