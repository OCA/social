# Copyright 2022-2023 Moduon Team S.L. <info@moduon.team>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase


class InstallationCase(TransactionCase):
    def test_cron_cadence(self):
        """Test that the post_init_hook was properly executed."""
        cron = self.env.ref("mail.ir_cron_mail_scheduler_action")
        cadence = cron.interval_number, cron.interval_type
        self.assertEqual(cadence, (1, "minutes"))
