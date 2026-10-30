# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res.setdefault(
            "autofollow_recipients", self.env.context.get("mail_post_autofollow", False)
        )
        return res

    autofollow_recipients = fields.Boolean(
        string="Make recipients followers",
        help="""if checked, the additional recipients will be added as\
        followers on the related object""",
    )

    def _action_send_mail(self, auto_commit=False):
        result_mails_su, result_messages = (
            self.env["mail.mail"].sudo(),
            self.env["mail.message"],
        )
        for wizard in self:
            result_mails_su_wizard, result_messages_wizard = super(
                MailComposeMessage,
                wizard.with_context(mail_post_autofollow=wizard.autofollow_recipients),
            )._action_send_mail(auto_commit=auto_commit)
            result_mails_su += result_mails_su_wizard
            result_messages += result_messages_wizard
        return result_mails_su, result_messages
