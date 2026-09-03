# Copyright 2026 Cetmix OÜ
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailGateway(models.Model):
    _inherit = "mail.gateway"

    gateway_type = fields.Selection(
        selection_add=[("instagram", "Instagram")], ondelete={"instagram": "cascade"}
    )
    instagram_security_key = fields.Char(
        help="Verify token Meta sends as hub.verify_token during webhook setup.",
    )
    instagram_account_id = fields.Char(
        help="Instagram professional account ID (IGID) used in the send URL.",
    )
    instagram_version = fields.Char(
        default="26.0",
        help="Graph API version without the v prefix, for example 26.0.",
    )
