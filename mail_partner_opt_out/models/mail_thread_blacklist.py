from odoo import models


class MailBlackListMixin(models.AbstractModel):
    _inherit = "mail.thread.blacklist"

    def mail_blacklist_add(self):
        for mail_thread_blacklist in self:
            if not mail_thread_blacklist.is_blacklisted and mail_thread_blacklist.email:
                self.env["mail.blacklist"].sudo()._add(mail_thread_blacklist.email)
