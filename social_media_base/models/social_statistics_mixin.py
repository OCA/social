# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SocialStatisticsMixin(models.AbstractModel):
    """Counters a social media reports for an account or for a publication.

    Both sides count the same interactions, so the counters, their sum and the
    extension point of the connectors live here once::

        class SocialAccount(models.Model):
            _name = "social.account"
            _inherit = ["social.statistics.mixin"]

    A connector that counts something else extends this mixin instead of each
    model: the fields and the override reach every model inheriting it.
    """

    _name = "social.statistics.mixin"
    _description = "Social Media Interaction Counters"

    comment_count = fields.Integer(default=0)
    like_count = fields.Integer(default=0)
    click_count = fields.Integer(default=0)
    share_count = fields.Integer(default=0)
    interactions_count = fields.Integer(
        compute="_compute_interactions_count",
        store=True,
        default=0,
        help="Interactions with the publication: clicks, likes, comments and "
        "shares.",
    )
    impression_count = fields.Integer(
        default=0,
        help="Total number of views, which may include multiple views by the "
        "same user.",
    )

    def _interaction_count_fields(self):
        """Return the counters that add up to ``interactions_count``.

        The extension point of the connectors: X reports retweets and quotes,
        which are interactions with the account or the publication like any
        other. The dependency of the compute is read from here, so adding a
        counter is one line and cannot get out of sync with the sum.

        :rtype: list
        """
        return ["click_count", "like_count", "share_count", "comment_count"]

    @api.depends(lambda self: self._interaction_count_fields())
    def _compute_interactions_count(self):
        for record in self:
            record.interactions_count = sum(
                record[fname] for fname in record._interaction_count_fields()
            )
