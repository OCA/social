# Copyright 2023 Quartile Limited
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import config


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model
    def create(self, vals):
        """Ignore blocking for other tests"""
        if config["test_enable"] and not self.env.context.get(
            "test_mail_message_restrict"
        ):
            return super(MailMessage, self).create(vals)
        if vals.get("message_type") == "comment":
            subtype = self.env["mail.message.subtype"].browse(vals.get("subtype_id"))
            if (
                vals.get("model") not in subtype.allow_send_model_ids.mapped("model")
                and not subtype.internal
            ):
                raise ValidationError(
                    _(
                        "Creating a message in this model is blocked."
                        "Please contact the system administrator as necessary."
                    )
                )
        return super(MailMessage, self).create(vals)
