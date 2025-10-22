from odoo import api, models
from odoo.tools import format_datetime


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.depends_context("display_full_attachment_name")
    def _compute_display_name(self):
        if not self.env.context.get("display_full_attachment_name"):
            return super()._compute_display_name()
        for attachment in self:
            names = [
                attachment.name,
                attachment.create_uid.name,
                format_datetime(self.env, attachment.create_date),
            ]
            attachment.display_name = " - ".join(names)
