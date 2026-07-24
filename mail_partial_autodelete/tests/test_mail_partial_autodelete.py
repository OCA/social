# Copyright 2021 Akretion (http://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.base.tests.common import BaseCommon


class TestStockMoveForcedLot(BaseCommon):
    def setUp(self):
        super().setUp()
        self.mail = self.env["mail.mail"].create(
            {
                "subject": "Test subject",
                "body_html": "example body",
                "email_to": "test@example.com",
                "email_from": self.env.user.email,
            }
        )

    def test_no_autodelete(self):
        self.mail.auto_delete = False
        self.mail._send()
        self.assertEqual(self.mail.body_html, "example body")

    def test_autodelete_only_purge(self):
        self.mail.auto_delete = True
        self.mail._send()
        self.assertEqual(self.mail.body_html, "")

    def test_autodelete_only_purge_debugmode(self):
        self.env["ir.config_parameter"].create(
            {"key": "mail_partial_autodelete_debugmode", "value": 1}
        )
        self.mail.auto_delete = True
        self.mail._send()
        self.assertEqual(self.mail.body_html, "example body")
