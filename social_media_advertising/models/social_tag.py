# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SocialTag(models.Model):
    """Free tag used to classify the social media campaigns."""

    _name = "social.tag"
    _description = "Social Tag"
    _order = "name"

    name = fields.Char(required=True)
