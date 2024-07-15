# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class MailingList(models.Model):
    _name = "mailing.list"
    _inherit = ["mailing.list", "mail.unsubscription.mixin"]

    not_cross_unsubscriptable = fields.Boolean(
        string="Not cross unsubscriptable",
        help="If you mark this field, this list won't be shown when "
        "unsubscribing from other mailing list, in the section: "
        "'Is there any other mailing list you want to leave?'",
    )

    def _update_subscription_from_email(self, email, opt_out=True, force_message=None):
        # Track opt_in/out to lists
        res = super()._update_subscription_from_email(email, opt_out, force_message)
        if not self:
            return res
        action = "unsubscription" if opt_out else "subscription"
        details = self.env.context.get("details")
        reason_id = self.env.context.get("reason_id")
        self._track_mail_unsubscription(
            email, action, list_ids=self, reason_id=reason_id, details=details
        )
        return res
