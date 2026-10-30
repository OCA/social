# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import json

from odoo.tests.common import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged("post_install", "-at_install")
class TestMailThreadCreateNoLog(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "TEST"})
        cls.message_model = cls.env["mail.message"]

    def test_message_fetch(self):
        session = self.authenticate("demo", "demo")

        response = self.url_open(
            "/mail/thread/messages",
            data=json.dumps(
                {
                    "params": {
                        "thread_model": self.partner._name,
                        "thread_id": self.partner.id,
                    }
                }
            ),
            headers={
                "Content-Type": "application/json",
                "Cookie": f"session_id={session.sid};",
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        create_msg = data["result"]["data"]["mail.message"][-1]

        # # We get a creation message
        self.assertEqual(create_msg["model"], self.partner._name)
        self.assertEqual(create_msg["res_id"], self.partner.id)
        self.assertEqual(create_msg["author"]["id"], self.env.user.partner_id.id)
        self.assertEqual(create_msg["body"], self.partner._creation_message())
        # But it doesn't exist in the DB
        self.assertFalse(self.message_model.browse(create_msg["id"]).exists())
