# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api
from odoo.tools.translate import _


class MailNotification(models.Model):
    _inherit = "res.partner"

    @api.model
    def _notify(
        self,
        message,
        rdata,
        record,
        force_send=False,
        send_after_commit=True,
        model_description=False,
        mail_auto_delete=True
    ):
        partner_ids = []
        for data in rdata:
            partner_ids.append(data['id'])

        additional_header = self.get_additional_header_with_recipient(
            partner_ids
        )
        message.body = additional_header + message.body
        res = super(
            MailNotification, self.with_context(notified_partners=self)
        )._notify(
            message,
            rdata,
            record,
            force_send,
            send_after_commit,
            model_description,
            mail_auto_delete,
        )
        return res

    @api.model
    def get_additional_header_with_recipient(self, recipients_ids):
        recipients = self.env['res.partner'].browse(recipients_ids)
        recipients_name = [recipient.name for recipient in recipients]
        additional_header = "<b>%s%s.</b><br /><br />" % (
            _("Also notified: "),
            ", ".join(recipients_name),
        )
        return additional_header
