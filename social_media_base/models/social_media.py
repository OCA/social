# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SocialMedia(models.Model):
    _name = "social.media"
    _inherit = "social.media.base.mixin"
    _description = "Social Media"

    """
        This model defines social networks.
    """

    name = fields.Char()
    description = fields.Text()
    media_type = fields.Selection(
        selection=[("other_social", "Other social")],
        readonly=True,
    )
    image = fields.Binary()

    def open_action_account(self):
        """
        Show wizard for creating a new social media account
        """
        pass