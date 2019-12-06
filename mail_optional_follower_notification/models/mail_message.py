# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model
    def create(self, values):
        ctx = self.env.context.copy()
        if not ctx.get("notify_followers") and values.get("partner_ids"):
            partner_list = self.resolve_2many_commands(
                "partner_ids", values.get("partner_ids"), fields=["id"]
            )
            ctx["force_partners_to_notify"] = [d["id"] for d in partner_list]
        return super(MailMessage, self.with_context(ctx)).create(values)

    @api.multi
    def _notify(
        self,
        record,
        msg_vals,
        force_send=False,
        send_after_commit=True,
        model_description=False,
        mail_auto_delete=True,
    ):
        res = super()._notify(
            record,
            msg_vals,
            force_send=force_send,
            send_after_commit=send_after_commit,
            model_description=model_description,
            mail_auto_delete=mail_auto_delete,
        )
        if self.env.context.get("force_partners_to_notify"):
            # Needaction only for recipients
            self.needaction_partner_ids = [
                (6, 0, self.env.context.get("force_partners_to_notify"))
            ]
        return res
