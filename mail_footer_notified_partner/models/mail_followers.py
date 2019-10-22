# © 2016 ACSONE SA/NV <https://acsone.eu>
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
        force_send,
        send_after_commit,
        model_description,
        mail_auto_delete,
    ):
        additional_footer = self.get_additional_footer_with_recipient(
            message.notification_ids
        )
        message.body += additional_footer
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
    def get_additional_footer_with_recipient(self, recipients):
        recipients_name = [recipient.display_name for recipient in recipients]
        additional_footer = "<br /><b>%s%s.</b><br />" % (
            _("Also notified: "),
            ", ".join(recipients_name),
        )
        return additional_footer
