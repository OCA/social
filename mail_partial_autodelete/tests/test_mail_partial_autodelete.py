# Copyright 2021 Akretion (http://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import SavepointCase


class TestMailPartialAutodeleteCase(SavepointCase):
    def setUp(self):
        super().setUp()
        self.mail = self.env["mail.mail"].create(
            {
                "body": "example body",
            }
        )

    def test_no_autodelete(self):
        self.mail.auto_delete = False
        self.mail._send()
        self.assertEqual(self.mail.body, "<p>example body</p>")

    def test_autodelete_only_purge(self):
        self.mail.auto_delete = True
        self.mail._send()
        self.assertEqual(self.mail.body, "")
