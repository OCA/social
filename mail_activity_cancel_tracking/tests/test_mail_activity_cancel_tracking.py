# Copyright 2025 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import new_test_user
from odoo.tests.common import HttpCase, tagged
from odoo.tools import mute_logger


@tagged("-at_install", "post_install")
class TestMailActivityCancelTracking(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test partner"})
        cls.user = new_test_user(cls.env, login="test-user")
        cls.mail_activity = cls.partner.activity_schedule(
            user_id=cls.user.id,
            activity_type_id=cls.env.ref("mail.mail_activity_data_todo").id,
            summary="Play Mario Kart",
        )
        # Set the user to prevent mail_activity_team from leaving the user empty.
        cls.mail_activity.user_id = cls.user

    def test_mail_activity_done(self):
        self.start_tour(
            f"/web#id={self.partner.id}&model=res.partner",
            "mail_activity_cancel_tracking_done",
            login="test-user",
        )

    def test_mail_activity_cancel(self):
        self.start_tour(
            f"/web#id={self.partner.id}&model=res.partner",
            "mail_activity_cancel_tracking_cancel",
            login="test-user",
        )

    @mute_logger("odoo.models.unlink")
    def test_record_unlink(self):
        # This process should not fail
        self.partner.unlink()
