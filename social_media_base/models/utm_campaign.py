# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models

_SOCIAL_GROUPS = "social_media_base.group_social_media_user"


class UtmCampaign(models.Model):
    """Social media publications promoting a marketing campaign."""

    _inherit = "utm.campaign"

    # The posts of the campaign, whatever their state. Like
    # ``mailing_mail_ids`` of ``mass_mailing``, they are not filtered by state:
    # the campaign is meant to show the work already planned, not only the
    # work already published.
    social_post_ids = fields.One2many(
        "social.post",
        "campaign_id",
        string="Social Media Posts",
        readonly=True,
        groups=_SOCIAL_GROUPS,
    )
    social_post_count = fields.Integer(
        string="Social Media Posts Count",
        compute="_compute_social_post_count",
        groups=_SOCIAL_GROUPS,
    )
    social_post_account_ids = fields.One2many(
        "social.post.account",
        "campaign_id",
        string="Social Media Publications",
        readonly=True,
        groups=_SOCIAL_GROUPS,
    )

    # A subset of the native ``click_count`` of the campaign, not a figure to
    # add to it: both count rows of ``link.tracker.click``, and this one only
    # keeps those that came from a social media publication.
    social_link_click_count = fields.Integer(
        string="Social Media Tracked Clicks",
        compute="_compute_social_link_click_count",
        help="Clicks Odoo registered on the tracked links of the social media "
        "publications of this campaign. Part of the clicks of the campaign, "
        "not something to add to them.",
        groups=_SOCIAL_GROUPS,
    )

    # The figures the social media report for the publications of the
    # campaign. They are prefixed because ``click_count`` already belongs to
    # ``link_tracker``, which counts something else: the clicks Odoo itself
    # registered on the tracked links of the campaign.
    social_click_count = fields.Integer(
        string="Social Media Clicks",
        compute="_compute_social_statistics",
        groups=_SOCIAL_GROUPS,
    )
    social_like_count = fields.Integer(
        string="Social Media Likes",
        compute="_compute_social_statistics",
        groups=_SOCIAL_GROUPS,
    )
    social_comment_count = fields.Integer(
        string="Social Media Comments",
        compute="_compute_social_statistics",
        groups=_SOCIAL_GROUPS,
    )
    social_share_count = fields.Integer(
        string="Social Media Shares",
        compute="_compute_social_statistics",
        groups=_SOCIAL_GROUPS,
    )
    social_impression_count = fields.Integer(
        string="Social Media Impressions",
        compute="_compute_social_statistics",
        groups=_SOCIAL_GROUPS,
    )
    social_interactions_count = fields.Integer(
        string="Social Media Interactions",
        compute="_compute_social_statistics",
        groups=_SOCIAL_GROUPS,
    )
    social_engagement = fields.Float(
        string="Social Media Engagement",
        compute="_compute_social_statistics",
        groups=_SOCIAL_GROUPS,
    )

    @api.depends("social_post_ids")
    def _compute_social_post_count(self):
        counts = {
            campaign.id: count
            for campaign, count in self.env["social.post"]._read_group(
                [("campaign_id", "in", self.ids)],
                ["campaign_id"],
                ["__count"],
            )
        }
        for campaign in self:
            # A campaign being edited is a virtual record whose posts are
            # those of the record it stands for.
            campaign.social_post_count = counts.get(
                campaign._origin.id or campaign.id, 0
            )

    def _compute_social_link_click_count(self):
        """Count the clicks Odoo registered on the links of the campaign.

        Neither stored nor declared with ``@api.depends``: storing it would
        turn every anonymous visit to a tracked link into an UPDATE on the row
        of the campaign, serializing concurrent clicks. Same reason as in
        ``social.post.account._compute_link_click_count``.

        No ``sudo()``: ``link_tracker`` gives read access to ``base.group_user``
        and declares no record rule, so the aggregate is the same for everyone.
        """
        counts = {
            campaign.id: count
            for campaign, count in self.env["link.tracker.click"]._read_group(
                [
                    ("campaign_id", "in", self.ids),
                    ("social_post_account_id", "!=", False),
                ],
                ["campaign_id"],
                ["__count"],
            )
        }
        for campaign in self:
            campaign.social_link_click_count = counts.get(campaign.id, 0)

    def _compute_social_statistics(self):
        """Aggregate what the social media report for the publications.

        Neither stored nor declared with ``@api.depends``, like
        ``utm.campaign._compute_statistics`` of ``mass_mailing``: the figures
        are refreshed by the social media on their own schedule, so they are
        read when a campaign is opened and never kept in the database.
        """
        self.update(
            {
                "social_click_count": 0,
                "social_like_count": 0,
                "social_comment_count": 0,
                "social_share_count": 0,
                "social_impression_count": 0,
                "social_interactions_count": 0,
                "social_engagement": 0.0,
            }
        )
        for (
            campaign,
            clicks,
            likes,
            comments,
            shares,
            impressions,
            interactions,
            engagement,
        ) in self.env["social.post.account"]._read_group(
            [("campaign_id", "in", self.ids)],
            ["campaign_id"],
            [
                "click_count:sum",
                "like_count:sum",
                "comment_count:sum",
                "share_count:sum",
                "impression_count:sum",
                "interactions_count:sum",
                # Added up, not averaged: the campaign and the card of a post
                # then answer the same question. Beware that a social media
                # reporting the engagement as a ratio over the impressions,
                # as LinkedIn does, is being added up here as well.
                "engagement:sum",
            ],
        ):
            campaign.social_click_count = clicks
            campaign.social_like_count = likes
            campaign.social_comment_count = comments
            campaign.social_share_count = shares
            campaign.social_impression_count = impressions
            campaign.social_interactions_count = interactions
            campaign.social_engagement = engagement or 0.0

    def action_view_social_posts(self):
        """Open the social media posts linked to this campaign."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Social Media Posts"),
            "res_model": "social.post",
            "view_mode": "kanban,tree,form",
            "domain": [("campaign_id", "=", self.id)],
            "context": {"default_campaign_id": self.id},
        }
