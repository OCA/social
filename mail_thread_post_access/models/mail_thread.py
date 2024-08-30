# Copyright 2024 CorporateHub
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def _get_mail_message_access(self, res_ids, operation, model_name=None):
        if operation in ["write", "unlink"]:
            check_operation = "write"
        elif operation == "create":
            if model_name is None:
                model_name = self._name
            mail_post_access = self.env["ir.model"]._get(model_name).mail_post_access
            if not mail_post_access:
                mail_post_access = getattr(
                    self.env[model_name] if model_name else self,
                    "_mail_post_access",
                    "write",
                )
            if mail_post_access in ["create", "read", "write", "unlink"]:
                check_operation = mail_post_access
            else:
                check_operation = "write"
        else:
            check_operation = operation
        return check_operation
