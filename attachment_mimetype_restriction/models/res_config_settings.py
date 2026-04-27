# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    attachment_allowed_mimetypes = fields.Char(
        related="company_id.attachment_allowed_mimetypes",
        string="Allowed Attachment Types",
        readonly=False,
    )
