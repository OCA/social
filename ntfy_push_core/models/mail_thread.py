# Copyright 2026 nurefexc (https://nurefexc.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, tools


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_post_after_hook(self, message, msg_vals):
        res = super()._message_post_after_hook(message, msg_vals)
        self._enqueue_ntfy_notification(message)
        return res

    def _enqueue_ntfy_notification(self, message):
        """Minimalist queueing with fixed high priority"""
        ntfy_users = message.partner_ids.user_ids.filtered(
            lambda u: u.notification_type == "ntfy" and u.id != self.env.uid
        )
        if not ntfy_users:
            return

        ntfy_users._check_ntfy_url_consistency()

        body_text = tools.html2plaintext(message.body or "")
        base_url = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url").rstrip("/")
        )
        link = f"{base_url}/web#model={self._name}&id={self.id}"

        queue_vals = [
            {
                "res_user_id": user.id,
                "title": f"{message.author_id.name or 'Odoo'}: {message.record_name or self._description}",
                "body": body_text[:250],
                "click_url": link,
            }
            for user in ntfy_users
        ]

        self.env["ntfy.notification.queue"].create(queue_vals)
