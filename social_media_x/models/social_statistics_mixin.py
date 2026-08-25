# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SocialStatisticsMixin(models.AbstractModel):
    """Counters X reports on top of the generic ones.

    The mixin is extended instead of each model because X counts retweets and
    quotes both on the account and on the publication.
    """

    _inherit = "social.statistics.mixin"

    retweet_count = fields.Integer(default=0)
    quote_count = fields.Integer(default=0)

    def _interaction_count_fields(self):
        """X counts retweets and quotes as interactions too."""
        return super()._interaction_count_fields() + ["retweet_count", "quote_count"]
