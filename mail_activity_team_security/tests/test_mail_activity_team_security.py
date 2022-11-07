# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields

from odoo.addons.mail_activity_security.tests.common import CommonMailActivitySecurity


class TestMailActivitySecurity(CommonMailActivitySecurity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.activity_team_a = cls.env["mail.activity.team"].create(
            {
                "name": "Team A",
                "user_id": cls.user_admin.id,
                "member_ids": [fields.Command.link(cls.user_demo.id)],
            }
        )
        cls.activity_team_b = cls.env["mail.activity.team"].create(
            {
                "name": "Team B",
                "user_id": cls.user_admin.id,
                "member_ids": [fields.Command.link(cls.user_test.id)],
            }
        )
        cls.activity.team_id = cls.activity_team_a

    def test_team_security(self):
        self.activity_type_task.security_edit = "owner"
        self.activity_type_task.security_done = "team"
        self.activity_type_task.security_cancel = "user"
        # Admin user can edit, mark as done and cancel
        self._test_activity_security(
            self.activity,
            user=self.user_admin,
            edit=True,
            done=True,
            cancel=True,
        )
        # Demo user can mark as done and cancel, but can't edit
        self._test_activity_security(
            self.activity,
            user=self.user_demo,
            edit=False,
            done=True,
            cancel=True,
        )
        # Test user can't do anything -- it's part of another team
        self._test_activity_security(
            self.activity,
            user=self.user_test,
            edit=False,
            done=False,
            cancel=False,
        )
