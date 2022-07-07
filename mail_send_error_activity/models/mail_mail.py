# Copyright (C) Cetmix OU <http://www.cetmix.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _prepare_mail_error_activity_vals(self):
        """
        Prepare mail error activity values
        :return: dict of values
        """
        self.ensure_one()
        users = self.author_id.user_ids
        record_ref = not (self.res_id and self.model)
        if not users or record_ref:
            return False
        if not issubclass(self.pool[self.model], self.pool["mail.activity.mixin"]):
            return False
        activity_type = self.env.ref(
            "mail_send_error_activity.mail_activity_data_mail_send_error"
        )
        return {
            "user_id": users[0].id,
            "activity_type_id": activity_type.id,
            "summary": "{} {}".format(
                activity_type.summary,
                ", ".join([partner.email for partner in self.partner_ids]),
            ),
            "note": self.failure_reason,
            "res_model_id": self.env["ir.model"]._get(self.model).id,
            "res_id": self.res_id,
        }

    def _postprocess_sent_message(
        self, success_pids, failure_reason=False, failure_type=None
    ):
        # Proceed on mail error only
        # and if enabled in settings
        if failure_type and self.env["ir.config_parameter"].sudo().get_param(
            "mail_send_error_activity.activity_on_mail_error", False
        ):
            for rec in self.filtered(
                lambda mail: mail.author_id and mail.state == "exception"
            ):
                vals = rec._prepare_mail_error_activity_vals()
                if vals:
                    self.env["mail.activity"].create(vals)
        return super(MailMail, self)._postprocess_sent_message(
            success_pids, failure_reason=failure_reason, failure_type=failure_type
        )
