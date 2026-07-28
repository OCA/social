# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SocialMedia(models.Model):
    """Social media supported by an installed connector module."""

    _name = "social.media"
    _inherit = "social.media.base.mixin"
    _description = "Social Media"

    name = fields.Char()
    description = fields.Text()
    media_type = fields.Selection(
        [],
        readonly=True,
    )
    image = fields.Binary()

    def open_action_account(self):
        """Return the wizard action to associate an account.

        Connector modules override it with their own wizard.

        :rtype: dict
        """
