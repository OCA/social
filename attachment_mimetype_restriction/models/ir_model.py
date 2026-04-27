# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class IrModel(models.Model):
    _inherit = "ir.model"

    attachment_allowed_mimetypes = fields.Char(
        string="Allowed Attachment Types",
        help="Comma-separated list of allowed MIME types for attachments on this "
        "model. Leave empty to use company's global configuration. "
        "Example: image/png,application/pdf. "
        "This configuration applies globally to all companies.",
    )
