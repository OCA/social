# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailMessage(models.Model):
    _inherit = "mail.message"

    def set_message_undone(self):
        """
        Reverses the effect of set_message_done() by:
        - Setting is_read to False on the notification
        - Moving the message from History back to Inbox
        - Updating the needaction counter
        """
        partner_id = self.env.user.partner_id

        notifications = (
            self.env["mail.notification"]
            .sudo()
            .search(
                [
                    ("mail_message_id", "in", self.ids),
                    ("res_partner_id", "=", partner_id.id),
                    ("is_read", "=", True),
                ]
            )
        )

        if not notifications:
            return

        notifications.write({"is_read": False})

        counter = self.env.user.partner_id._get_needaction_count()
        self.env["bus.bus"]._sendone(
            partner_id,
            "mail.message/mark_as_unread",
            {
                "message_ids": notifications.mail_message_id.ids,
                "needaction_inbox_counter": counter,
            },
        )
