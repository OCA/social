# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class SocialPost(models.Model):
    """Link a post to the social media campaign promoting it.

    ``social_campaign_id`` is the campaign of the social media, the one
    holding the budget and the remote reference used to publish a sponsored
    post. It is independent of ``campaign_id``, the Odoo marketing campaign
    the base module declares and the other applications share.
    """

    _inherit = "social.post"

    social_campaign_id = fields.Many2one("social.advertising.campaign")
    allow_social_campaign_ids = fields.Many2many(
        "social.advertising.campaign",
        compute="_compute_allow_social_campaign_ids",
        help="Social media campaigns that can be linked to this post.",
    )

    def _get_locked_content_fields(self):
        """Freeze the campaign too: it decides how the post is published."""
        return super()._get_locked_content_fields() + ("social_campaign_id",)

    @api.depends("account_ids.media_id.media_type")
    @api.depends_context("uid")
    def _compute_allow_social_campaign_ids(self):
        SocialAdvertisingCampaign = self.env["social.advertising.campaign"]
        # Posts sharing the same accounts share the same domain, so each
        # distinct one is searched once instead of once per post.
        campaign_ids_by_domain = {}
        for post in self:
            domain = post._get_allow_social_campaign_domain()
            key = repr(domain)
            if key not in campaign_ids_by_domain:
                campaign_ids_by_domain[key] = SocialAdvertisingCampaign.search(
                    domain
                ).ids
            post.allow_social_campaign_ids = [Command.set(campaign_ids_by_domain[key])]

    @api.onchange("allow_social_campaign_ids")
    def _onchange_allow_social_campaign_ids(self):
        """Drop the social media campaign once the post no longer accepts it.

        The allowed campaigns depend on the content of the post, so editing it
        can invalidate a campaign already chosen. Odoo keeps a many2one that
        falls out of its domain, and the post would only fail when published,
        so it is cleared here instead. A post whose content is frozen is left
        untouched: its campaign is readonly and already published.

        The records are compared through ``_origin`` because the onchange runs
        on a virtual record, where the computed campaigns carry ``NewId``
        identifiers while the chosen one is a stored record.
        """
        for post in self:
            if post.state != "draft" or post.content_locked:
                continue
            campaign = post.social_campaign_id._origin
            if campaign and campaign not in post.allow_social_campaign_ids._origin:
                post.social_campaign_id = False

    def _get_allow_social_campaign_domain(self):
        """Return the domain of the social media campaigns of this post.

        Connector modules extend it with their own restrictions.

        :rtype: list
        """
        self.ensure_one()
        return [
            (
                "media_id.media_type",
                "in",
                self.account_ids.mapped("media_id.media_type"),
            )
        ]
