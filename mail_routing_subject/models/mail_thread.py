# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import api, models
from odoo.tools.mail import email_split


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_route(
        self, message, message_dict, model=None, thread_id=None, custom_values=None
    ):
        try:
            return super().message_route(
                message,
                message_dict,
                model=model,
                thread_id=thread_id,
                custom_values=custom_values,
            )
        except ValueError:
            route = self._message_route_mail_routing_subject(
                message, message_dict, custom_values=custom_values
            )
            if not route:
                raise
            return route

    def _message_route_mail_routing_subject(
        self, message, message_dict, custom_values=None
    ):
        """
        Return route(s) searching for mails the message might be a reply to
        by matching subjects
        """
        prefixes = (
            self.env["ir.config_parameter"]
            .get_param("mail_routing_subject.prefixes", "")
            .split()
        )
        if not prefixes:
            return []
        subject = message_dict["subject"]
        if not any(subject.startswith(prefix) for prefix in prefixes):
            return []

        while True:
            for prefix in prefixes:
                if subject.startswith(prefix):
                    subject = subject[len(prefix) :].lstrip()
                    break
            else:
                break

        email = "".join(email_split(message_dict["email_from"]))
        return [
            (
                mail.model,
                mail.res_id,
                custom_values,
                self.env.user.id,
                self.env["mail.alias"],
            )
            for mail in self.env["mail.message"].search(
                [
                    ("subject", "=", subject),
                    "|",
                    "|",
                    "|",
                    ("mail_ids.email_to", "like", email),
                    ("mail_ids.email_cc", "like", email),
                    ("mail_ids.recipient_ids.email", "=", email),
                    ("notification_ids.res_partner_id.email", "=", email),
                ]
            )
        ]
