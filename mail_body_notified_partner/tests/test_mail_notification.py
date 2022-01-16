# © 2016 ACSONE SA/NV <https://acsone.eu>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import odoo.tests.common as common


class TestMailNotification(common.TransactionCase):
    def test_get_signature_footer(self):
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
