# Copyright 2022-2023 Moduon Team S.L. <info@moduon.team>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import datetime, timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        """Defer emails by default."""
        _self = self
        if "mail_defer_seconds" not in _self.env.context:
            force_send = _self.env.context.get("mail_notify_force_send") or kwargs.get(
                "force_send", False
            )
            kwargs.setdefault("force_send", force_send)
            if not force_send:
                # If deferring message, give the user some minimal time to revert it
                _self = _self.with_context(mail_defer_seconds=30)
        defer_seconds = _self.env.context.get("mail_defer_seconds")
        if defer_seconds:
            kwargs.setdefault(
                "scheduled_date",
                datetime.utcnow() + timedelta(seconds=defer_seconds),
            )
        return super(MailThread, _self)._notify_thread(
            message, msg_vals=msg_vals, **kwargs
        )

    def _check_can_update_message_content(self, messages):
        """Allow updating unsent messages.

        Upstream Odoo only allows updating notes. We want to be able to update
        any message that is not sent yet. When a message is scheduled,
        notifications and mails will still not exist. Another possibility is
        that they exist but are not sent yet. In those cases, we are still on
        time to update it.
        """
        try:
            # If upstream allows editing, we are done
            return super()._check_can_update_message_content(messages)
        except UserError:
            # Repeat upstream checks that are still valid for us
            if messages.tracking_value_ids:
                raise
            if any(message.message_type != "comment" for message in messages):
                raise
            # Check that no notification or mail has been sent yet
            if any(
                ntf.notification_status == "sent" for ntf in messages.notification_ids
            ):
                raise UserError(
                    _("Cannot modify message; notifications were already sent.")
                ) from None
            if any(mail.state in {"sent", "received"} for mail in messages.mail_ids):
                raise UserError(
                    _("Cannot modify message; notifications were already sent.")
                ) from None

    def _message_update_content(self, *args, **kwargs):
        """Defer messages by extra 30 seconds after updates."""
        kwargs.setdefault(
            "scheduled_date", fields.Datetime.now() + timedelta(seconds=30)
        )
        return super()._message_update_content(*args, **kwargs)
