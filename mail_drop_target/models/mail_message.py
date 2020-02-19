from odoo import api, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.multi
    def _notify(
        self, record, msg_vals, force_send=False, send_after_commit=True,
        model_description=False, mail_auto_delete=True
    ):
        if self.env.context.get('message_create_from_mail_mail', False):
            return
        return super()._notify(
            record, msg_vals, force_send=force_send,
            send_after_commit=send_after_commit,
            model_description=model_description,
            mail_auto_delete=mail_auto_delete)
