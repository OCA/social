# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase


class CommonMailActivitySecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.user_admin = cls.env.ref("base.user_admin")
        cls.user_demo = cls.env.ref("base.user_demo")
        cls.user_test = cls.user_demo.copy({"name": "Test User", "login": "test"})
        cls.activity_type_task = cls.env["mail.activity.type"].create(
            {
                "name": "Task",
                "icon": "fa-tasks",
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.activity = cls.partner.activity_schedule(
            summary="Something to do",
            note="Please do it ASAP",
            activity_type_id=cls.activity_type_task.id,
            user_id=cls.user_demo.id,
            create_uid=cls.user_admin.id,
        )

    def _test_activity_security(
        self, activity, user=None, edit=None, done=None, cancel=None
    ):
        if user:
            activity = activity.with_user(user.id)
        expected = {}
        if edit is not None:
            expected["edit"] = edit
        if done is not None:
            expected["done"] = done
        if cancel is not None:
            expected["cancel"] = cancel
        for action, allowed in expected.items():
            if allowed:
                activity.check_activity_security(action)
            else:
                with self.assertRaises(
                    AccessError, msg=f"{action} should not be allowed"
                ):
                    activity.check_activity_security(action)
