# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    notify_followers = fields.Boolean(default=True)

    def _action_send_mail(self, auto_commit=False):
        result_mails_su, result_messages = (
            self.env["mail.mail"].sudo(),
            self.env["mail.message"],
        )
        for wizard in self:
            wizard = wizard.with_context(notify_followers=wizard.notify_followers)
            result_mails_su_wizard, result_messages_wizard = super(
                MailComposeMessage, wizard
            )._action_send_mail(auto_commit=auto_commit)
            result_mails_su += result_mails_su_wizard
            result_messages += result_messages_wizard
        return result_mails_su, result_messages
