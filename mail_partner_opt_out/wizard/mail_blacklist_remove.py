from odoo import models


class MailBlacklistRemove(models.TransientModel):
    _inherit = "mail.blacklist.remove"

    def action_unblacklist_apply(self):
        email_list = [email.strip() for email in self.email.split(",")]
        for email in email_list:
            self.env["mail.blacklist"].action_remove_with_reason(email, self.reason)
        return {"type": "ir.actions.act_window_close"}
