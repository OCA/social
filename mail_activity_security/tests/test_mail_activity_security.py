# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields

from .common import CommonMailActivitySecurity


class TestMailActivitySecurity(CommonMailActivitySecurity):
    def test_default_behaviour(self):
        """Test the default behaviour (all)

        It acts exactly like with standard Odoo: all users can edit, mark as done
        as long as they have access to the record.
        """
        # Admin user can edit, mark as done and cancel
        self._test_activity_security(
            self.activity,
            user=self.user_admin,
            edit=True,
            done=True,
            cancel=True,
        )
        # Demo user can edit, mark as done and cancel
        self._test_activity_security(
            self.activity,
            user=self.user_demo,
            edit=True,
            done=True,
            cancel=True,
        )
        # Test user can edit, mark as done and cancel
        self._test_activity_security(
            self.activity,
            user=self.user_test,
            edit=True,
            done=True,
            cancel=True,
        )

    def test_security_user_assigned(self):
        """
        Only the assigned user is allowed to mark it as done.
        And only the user who created the activity can edit or cancel it.
        """
        self.activity_type_task.security_done = "user"
        self.activity_type_task.security_edit = "owner"
        self.activity_type_task.security_cancel = "owner"
        # Admin user can edit, mark as done and cancel
        self._test_activity_security(
            self.activity,
            user=self.user_admin,
            edit=True,
            done=True,
            cancel=True,
        )
        # Demo user can only mark as done
        self._test_activity_security(
            self.activity,
            user=self.user_demo,
            edit=False,
            done=True,
            cancel=False,
        )
        # Test user can't do anything with it
        self._test_activity_security(
            self.activity,
            user=self.user_test,
            edit=False,
            done=False,
            cancel=False,
        )

    def test_security_owner(self):
        """
        Only the assigned user is allowed to mark it as done.
        But test user is the one who created the activity, so he has superpowers
        """
        self.activity_type_task.security_done = "user"
        self.activity_type_task.security_edit = "owner"
        self.activity_type_task.security_cancel = "owner"
        self.activity.create_uid = self.user_test
        self._test_activity_security(
            self.activity,
            user=self.user_test,
            edit=True,
            done=True,
            cancel=True,
        )

    def test_security_group(self):
        """
        Only the assigned user is allowed to mark it as done.
        But test user is part of the management group, so he has superpowers
        """
        self.activity_type_task.security_edit = "owner"
        self.activity_type_task.security_done = "user"
        self.activity_type_task.security_cancel = "owner"
        group = self.env["res.groups"].create({"name": "Task Management"})
        self.activity_type_task.security_group_ids = [fields.Command.link(group.id)]
        self.user_test.groups_id = [fields.Command.link(group.id)]
        self._test_activity_security(
            self.activity,
            user=self.user_test,
            edit=True,
            done=True,
            cancel=True,
        )
