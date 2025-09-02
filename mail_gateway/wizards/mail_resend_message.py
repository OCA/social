from odoo import Command, api, fields, models


class MailResendMessage(models.TransientModel):
    _inherit = "mail.resend.message"

    gateway_notification_ids = fields.Many2many(
        "mail.notification",
        relation="mail_resend_message_gateway_notification_rel",
        string="Gateway Notifications",
        readonly=True,
    )

    @api.model
    def default_get(self, fields):
        values = super().default_get(fields)
        message_id = self._context.get("mail_message_to_resend")
        if message_id:
            mail_message_id = self.env["mail.message"].browse(message_id)
            notification_ids = mail_message_id.notification_ids.filtered(
                lambda notif: notif.notification_type == "gateway"
                and notif.notification_status == "exception"
            )
            values["gateway_notification_ids"] = [Command.set(notification_ids.ids)]
        return values
