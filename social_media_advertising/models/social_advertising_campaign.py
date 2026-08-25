# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class SocialAdvertisingCampaign(models.Model):
    """Campaign used to promote the posts of a social media account."""

    _name = "social.advertising.campaign"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Social Advertising Campaign"
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    campaign_group_id = fields.Many2one(
        "social.advertising.campaign.group", string="Campaign Group", tracking=True
    )
    allow_media_ids = fields.Many2many(
        "social.media",
        string="Allowed Media",
        compute="_compute_allow_media_ids",
    )
    media_id = fields.Many2one(
        "social.media", string="Media", domain="[('id', 'in', allow_media_ids)]"
    )
    media_type = fields.Selection(related="media_id.media_type")
    account_ids = fields.Many2many(
        "social.account",
        relation="social_advertising_campaign_account_rel",
        column1="campaign_id",
        column2="account_id",
        string="Accounts",
        domain="[('media_id', 'in', allow_media_ids)]",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        required=True,
        index=True,
        default=lambda self: self.env.user,
        tracking=True,
        help="User this campaign belongs to. Only the responsible user and "
        "the social media administrators can see it.",
    )
    tag_ids = fields.Many2many(
        "social.tag",
        relation="social_advertising_campaign_tag_rel",
        column1="campaign_id",
        column2="tag_id",
        string="Tags",
    )
    stage_id = fields.Many2one(
        "social.stage",
        string="Stage",
        copy=False,
        index=True,
        tracking=True,
        domain="[('media_id', '=', media_id), ('applies_to', '=', 'campaign')]",
        help="Status of this campaign on the social media.",
    )
    stage_level = fields.Selection(related="stage_id.level")
    remote_ref = fields.Char(
        string="Remote Reference",
        copy=False,
        index=True,
        help="Identifier of this campaign on the social media. It is set by "
        "the connector module of each social media.",
    )
    advertising_account_id = fields.Many2one(
        "social.advertising.account",
        readonly=True,
        copy=False,
        index=True,
        ondelete="set null",
        help="Advertising account this campaign belongs to on the social "
        "media. It is set when the campaign is created there or imported "
        "from it, and never changes afterwards, except when the advertising "
        "account itself disappears from the social media: it is then dropped "
        "and this campaign is left without a link.",
    )

    _sql_constraints = [
        (
            "remote_ref_uniq",
            "unique(remote_ref, media_id)",
            "The remote reference must be unique per social media.",
        ),
    ]

    @api.depends("media_id", "account_ids")
    def _compute_allow_media_ids(self):
        SocialMedia = self.env["social.media"]
        # The allowed media types repeat across records, so each distinct
        # set is searched once instead of once per campaign.
        media_ids_by_types = {}
        for campaign in self:
            media_types = tuple(campaign._available_campaign())
            if media_types not in media_ids_by_types:
                media_ids_by_types[media_types] = SocialMedia.search(
                    [("media_type", "in", list(media_types))]
                ).ids
            campaign.allow_media_ids = [Command.set(media_ids_by_types[media_types])]

    @api.depends("name", "media_id")
    def _compute_display_name(self):
        for campaign in self:
            media_type = campaign.media_id.media_type
            campaign.display_name = (
                f"[{media_type.upper()}] {campaign.name}"
                if media_type and campaign.name
                else campaign.name
            )

    def _available_campaign(self):
        """Return the media types allowed on a campaign.

        Connector modules append their own.

        :rtype: list
        """
        return []
