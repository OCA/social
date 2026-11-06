# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SocialPost(models.Model):
    """Facebook has no extra constraints beyond the base ones."""

    _inherit = "social.post"
