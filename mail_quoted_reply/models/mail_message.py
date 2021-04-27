# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailMessage(models.Model):

    _inherit = 'mail.message'

    def reply_message(self):
        action = self.env.ref(
            "mail.action_email_compose_message_wizard"
        ).read()[0]
        action['context'] = {
            "default_model": self._name,
            "default_res_id": self.id,
            "default_template_id": self.env.ref(
                "mail_quoted_reply.reply_template"
            ).id,
            "default_composition_mode": "comment",
            "default_is_log": False,
            "is_log": False,
            "default_notify": True,
            "force_email": True,
            "reassign_to_parent": True,
            "default_partner_ids": [
                (6, 0, self.partner_ids.ids)
            ]
        }
        return action
