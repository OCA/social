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

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        """Defer emails by default."""
        defer_seconds = self.env.context.get("mail_defer_seconds")
        if defer_seconds:
            kwargs.setdefault(
                "scheduled_date",
                fields.Datetime.now() + timedelta(seconds=defer_seconds),
            )
        return super()._notify_thread(message, msg_vals=msg_vals, **kwargs)

    def _check_can_update_message_content(self, message):
        """Allow deleting unsent mails.

        When a message is scheduled, notifications and mails will still not
        exist. Another possibility is that they exist but are not sent yet. In
        those cases, we are still on time to update it. Once they are sent,
        it's too late.
        """
        if (
            self.env.context.get("deleting")
            and (
                not message.notification_ids
                or set(message.notification_ids.mapped("notification_status"))
                == {"ready"}
            )
            and (
                not message.mail_ids
                or set(message.mail_ids.mapped("state")) == {"outgoing"}
            )
        ):
            return
        return super()._check_can_update_message_content(message)

    def _message_update_content(self, message, body, *args, **kwargs):
        """Let checker know about empty body."""
        _self = self.with_context(deleting=body == "")
        return super(MailThread, _self)._message_update_content(
            message, body, *args, **kwargs
        )
