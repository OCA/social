from odoo import models


class MailBlackListMixin(models.AbstractModel):
    _inherit = "mail.thread.blacklist"

    def mail_blacklist_add(self):
        for rec in self:
            if not rec.is_blacklisted and rec.email:
                self.env["mail.blacklist"].sudo()._add(self.email)
