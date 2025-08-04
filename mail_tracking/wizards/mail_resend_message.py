# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, api, models


class MailResendMessage(models.TransientModel):
    _inherit = "mail.resend.message"

    @api.model
    def default_get(self, fields):
        rec = super().default_get(fields)
        message_id = self._context.get("mail_message_to_resend")
        if not message_id:
            return rec
        mail_message = self.env["mail.message"].browse(message_id)
        failed_states = self.env["mail.message"].get_failed_states()
        tracking_ids = mail_message.mail_tracking_ids.filtered(
            lambda x: x.state in failed_states
        )
        if tracking_ids:
            partner_values = []
            for tracking in tracking_ids:
                notification = mail_message.notification_ids.filtered(
                    lambda x, tracking=tracking: x.res_partner_id == tracking.partner_id
                )
                existing_resend_partner = self.env["mail.resend.partner"].search(
                    [("notification_id", "=", notification.id)]
                )
                if existing_resend_partner:
                    rec["partner_ids"].extend(
                        [Command.link(existing_resend_partner.id)]
                    )
                    continue
                # Create only resends that mail.notification didn't prepare already
                partner_values.append(
                    {
                        "notification_id": notification.id,
                        "resend": True,
                        "message": tracking.error_description,
                    }
                )
            if partner_values:
                partner_ids = self.env["mail.resend.partner"].create(partner_values).ids
                partner_commands = [
                    Command.link(partner_id) for partner_id in partner_ids
                ]
                rec["partner_ids"].extend(partner_commands)
        return rec

    def resend_mail_action(self):
        for wizard in self:
            to_send = wizard.partner_ids.filtered("resend").mapped("partner_id")
            if to_send:
                # Set as reviewed
                wizard.mail_message_id.mail_tracking_needs_action = False
                # Reset mail.tracking.email state
                tracking_ids = wizard.mail_message_id.mail_tracking_ids.filtered(
                    lambda x, to_send=to_send: x.partner_id in to_send
                )
                tracking_ids.sudo().write({"state": False})
        res = super().resend_mail_action()
        failed_states = self.env["mail.message"].get_failed_states()
        for wizard in self:
            to_send = wizard.partner_ids.filtered("resend").mapped("partner_id")
            if to_send:
                tracking_ids = wizard.mail_message_id.mail_tracking_ids.filtered(
                    lambda x, to_send=to_send, failed_states=failed_states: x.partner_id
                    in to_send
                    and x.state in failed_states
                )
                # Send bus notifications to update Discuss
                self.env["bus.bus"]._sendone(
                    self.env.user.partner_id,
                    "mail.tracking/toggle_tracking_status",
                    {
                        "message_ids": self.mail_message_id.ids,
                        "still_failed": bool(tracking_ids),
                    },
                )
        return res
