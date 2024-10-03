# Copyright 2024 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import Command, _, api, models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.model
    def get_record_data(self, values):
        result = super().get_record_data(values)
        re_prefix = _("Re:")
        fwd_prefix = _("Fwd:")
        if self.env.context.get("message_forwarded_id"):
            # remove 'Re: ' prefixes and add 'Fwd:' prefix to the subject
            subject = result.get("subject")
            if subject and subject.startswith(re_prefix):
                subject = "%s %s" % (fwd_prefix, subject[4:])
            result["subject"] = subject
        return result

    def _action_send_mail(self, auto_commit=False):
        # duplicate attachments from original message
        message_forwarded_id = self.env.context.get("message_forwarded_id")
        if message_forwarded_id:
            message_forwarded = self.env["mail.message"].browse(message_forwarded_id)
            for wizard in self:
                new_attachment_ids = []
                for attachment in wizard.attachment_ids:
                    if attachment in message_forwarded.attachment_ids:
                        new_attachment = attachment.copy(
                            {"res_model": "mail.compose.message", "res_id": wizard.id}
                        )
                        new_attachment_ids.append(new_attachment.id)
                    else:
                        new_attachment_ids.append(attachment.id)
                new_attachment_ids.reverse()
                wizard.write({"attachment_ids": [Command.set(new_attachment_ids)]})
        return super()._action_send_mail(auto_commit=auto_commit)
