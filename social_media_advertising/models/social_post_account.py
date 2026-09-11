# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SocialPostAccount(models.Model):
    """Link a publication to the campaigns promoting it."""

    _inherit = "social.post.account"

    social_campaign_id = fields.Many2one(
        "social.advertising.campaign",
        compute="_compute_social_campaign_id",
        store=True,
        readonly=False,
        help="Social media campaign of the parent post. A publication "
        "imported from the social media has no parent post, so its campaign "
        "is resolved by the connector module from the remote one.",
    )

    @api.depends("post_id.social_campaign_id")
    def _compute_social_campaign_id(self):
        """Propagate the social media campaign of the parent post."""
        for post_account in self.filtered("post_id"):
            post_account.social_campaign_id = post_account.post_id.social_campaign_id

    def _action_campaign_post(self, post_id):
        """Publish the campaign post on the social media.

        :param post_id: the ``social.post`` being published.
        :return: the remote reference of the sponsored creative (stored by
            the connector module in its own field), or ``None`` when the
            publication is not sponsored.
        """
