# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Base settings model for Social Media Integration
    # Platform-specific credentials are defined in their respective modules:
    # - Facebook: social_media_facebook
    # - LinkedIn: social_media_linkedin
    # - X (Twitter): social_media_x
    pass
