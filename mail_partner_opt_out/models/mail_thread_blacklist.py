from odoo import models


class MailBlackListMixin(models.AbstractModel):
    _inherit = "mail.thread.blacklist"

    def mail_blacklist_add(self):
        for rec in self:
            if not rec.is_blacklisted and rec.email:
                self.env["mail.blacklist"].sudo()._add(rec.email)

    def mail_action_blacklist_remove(self):
        emails_list = [
            record.email for record in self if record.email and record.is_blacklisted
        ]
        emails_str = ",".join(emails_list)
        context = self.env.context.copy()
        context["default_email"] = emails_str
        res = super(MailBlackListMixin, self).mail_action_blacklist_remove()
        res["context"] = context
        return res
