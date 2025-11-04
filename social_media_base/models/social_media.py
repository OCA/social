# Copyright 2025 Kencove (https://www.kencove.com/)
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
        [],
        readonly=True,
    )
    image = fields.Binary()

    def open_action_account(self):
        pass
