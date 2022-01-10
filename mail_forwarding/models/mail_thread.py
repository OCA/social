from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, **kwargs):
        if kwargs.get("partner_ids", False):
            users = self.env["res.users"].search(
                [
                    ("partner_id", "in", kwargs["partner_ids"]),
                    ("share", "=", False),
                    ("forwarding_user_id", "!=", False),
                    ("forwarding_user_id.partner_id", "not in", kwargs["partner_ids"]),
                ]
            )
            kwargs["partner_ids"].append(
                users.mapped("forwarding_user_id.partner_id").ids
            )
        return super().message_post(**kwargs)
