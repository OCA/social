# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResUsers(models.Model):
    """Remember whether the user asked for the dark palette."""

    _inherit = "res.users"

    social_dark_mode = fields.Boolean(
        string="Social Media Dark Mode",
        help="Draw the web client with the dark palette of the social media "
        "screens. It is the same answer for every browser of the user.",
    )

    @api.model
    def get_social_dark_mode(self):
        """Read the palette of the user asking, without exposing the record."""
        return bool(self.env.user.social_dark_mode)

    @api.model
    def set_social_dark_mode(self, enabled):
        """Store the palette of the user asking.

        A user may write their own preferences but not every field of
        ``res.users`` through a plain write, so the field is written as the
        user, with sudo, and only on the record of the caller.
        """
        self.env.user.sudo().write({"social_dark_mode": bool(enabled)})
        return bool(enabled)
