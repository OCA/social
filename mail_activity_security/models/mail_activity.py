# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import AccessError


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def check_activity_security(self, operation: str) -> bool:
        if self.env.context.get("bypass_activity_security"):
            return True
        if any(not rec._check_activity_security(operation) for rec in self):
            if operation == "edit":
                raise AccessError(_("You are not allowed to edit this activity."))
            if operation == "done":
                raise AccessError(
                    _("You are not allowed to mark this activity as done.")
                )
            if operation == "cancel":
                raise AccessError(_("You are not allowed to cancel this activity."))
            raise AccessError(_("You're not allowed to perform this operation."))
        return True

    def _check_activity_security(self, operation: str) -> bool:
        self.ensure_one()
        if not self.activity_type_id:
            return True
        if self._user_is_activity_security_admin():
            return True
        # Check all applicable rules according to the configured level
        rules = self.activity_type_id._get_activity_security_rules(operation)
        return any(self._check_activity_security_rule(rule) for rule in rules)

    def _user_is_activity_security_admin(self):
        """Checks if the current user is part of the activity admins"""
        self.ensure_one()
        return (
            self.env.is_superuser()
            or self.env.is_admin()
            or any(
                g in self.env.user.groups_id
                for g in self.activity_type_id.security_group_ids
            )
        )

    def _check_activity_security_rule(self, rule: str) -> bool:
        self.ensure_one()
        user = self.env.user
        if rule == "owner" and self.create_uid == user:
            return True
        if rule == "user" and self.user_id == user:
            return True
        if rule == "all":
            return True
        return False

    def activity_format(self):
        res = super().activity_format()
        for item in res:
            rec = self.browse(item["id"])
            item.update(
                {
                    "user_can_mark_as_done": rec._check_activity_security("done"),
                    "user_can_edit": rec._check_activity_security("edit"),
                    "user_can_cancel": rec._check_activity_security("cancel"),
                }
            )
        return res

    def _action_done(self, feedback=False, attachment_ids=None):
        self.check_activity_security("done")
        self = self.with_context(bypass_activity_security=True)
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def write(self, vals):
        self.check_activity_security("edit")
        return super().write(vals)

    def unlink(self):
        self.check_activity_security("cancel")
        return super().unlink()
