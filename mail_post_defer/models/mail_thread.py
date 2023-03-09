# Copyright 2022-2023 Moduon Team S.L. <info@moduon.team>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import timedelta

from odoo import fields, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_post(self, **kwargs):
        """Post messages using queue by default."""
        _self = self
        force_send = self.env.context.get("mail_notify_force_send") or kwargs.get(
            "force_send", False
        )
        kwargs.setdefault("force_send", force_send)
        if not force_send:
            # If deferring message, give the user some minimal time to revert it
            _self = self.with_context(mail_defer_seconds=30)
        return super(MailThread, _self).message_post(**kwargs)

    def _notify_by_email_add_values(self, base_mail_values):
        """Defer emails by default."""
        result = super()._notify_by_email_add_values(base_mail_values)
        defer_seconds = self.env.context.get("mail_defer_seconds")
        if defer_seconds:
            result.setdefault(
                "scheduled_date",
                fields.Datetime.now() + timedelta(seconds=defer_seconds),
            )
        return result

    def _check_can_update_message_content(self, message):
        """Allow deleting unsent mails."""
        if (
            self.env.context.get("deleting")
            and set(message.notification_ids.mapped("notification_status")) == {"ready"}
            and set(message.mail_ids.mapped("state")) == {"outgoing"}
        ):
            return
        return super()._check_can_update_message_content(message)
