# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class SocialAdvertisingCampaignGroup(models.Model):
    """Set of campaigns managed as a unit on the social media."""

    _name = "social.advertising.campaign.group"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Social Advertising Campaign Group"
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    campaign_ids = fields.One2many("social.advertising.campaign", "campaign_group_id")
    campaign_count = fields.Integer(compute="_compute_campaign_count")
    media_id = fields.Many2one(
        "social.media",
        string="Media",
        compute="_compute_media_id",
        store=True,
        readonly=False,
        help="Social media of the campaigns of this group. Deduced from the "
        "campaigns; editable while the group has none, which is how a "
        "connector module knows the social media of a group created empty.",
    )
    stage_id = fields.Many2one(
        "social.stage",
        string="Stage",
        copy=False,
        index=True,
        tracking=True,
        domain="[('media_id', '=', media_id), ('applies_to', '=', 'group')]",
        help="Status of this campaign group on the social media.",
    )
    stage_level = fields.Selection(related="stage_id.level")
    remote_ref = fields.Char(
        string="Remote Reference",
        copy=False,
        index=True,
        help="Identifier of this campaign group on the social media. It is "
        "set by the connector module of each social media.",
    )
    advertising_account_id = fields.Many2one(
        "social.advertising.account",
        readonly=True,
        copy=False,
        index=True,
        ondelete="set null",
        help="Advertising account this campaign group belongs to on the "
        "social media. It is set when the campaign group is created there "
        "or imported from it, and never changes afterwards, except when the "
        "advertising account itself disappears from the social media: it is "
        "then dropped and this campaign group is left without a link.",
    )

    _sql_constraints = [
        (
            "remote_ref_uniq",
            "unique(remote_ref, media_id)",
            "The remote reference must be unique per social media.",
        ),
    ]

    @api.depends("campaign_ids.media_id")
    def _compute_media_id(self):
        """Deduce the media of the group from its campaigns.

        The single distinct media of the campaigns wins; campaigns of mixed
        medias reset the field. When no campaign carries a media the current
        value is re-assigned: this field is a stored editable compute, so
        Odoo initializes its cache from the database before computing and
        reading it back is the standard pattern (used by core, e.g. on
        account journals or on mailings) to keep a manually chosen value.
        """
        for group in self:
            medias = group.campaign_ids.media_id
            if len(medias) == 1:
                group.media_id = medias
            elif medias:
                group.media_id = False
            else:
                group.media_id = group.media_id

    @api.depends("campaign_ids")
    def _compute_campaign_count(self):
        counts = dict(
            self.env["social.advertising.campaign"]._read_group(
                [("campaign_group_id", "in", self.ids)],
                ["campaign_group_id"],
                ["__count"],
            )
        )
        for group in self:
            group.campaign_count = counts.get(group, 0)

    def action_view_campaigns(self):
        """Open the campaigns linked to this campaign group."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Campaigns"),
            "res_model": "social.advertising.campaign",
            "view_mode": "tree,form",
            "domain": [("campaign_group_id", "=", self.id)],
            "context": {"default_campaign_group_id": self.id},
        }
