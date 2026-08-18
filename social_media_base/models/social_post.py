# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import Command, api, fields, models
from odoo.exceptions import MissingError, UserError


class SocialPost(models.Model):
    _name = "social.post"
    _inherit = ["mail.thread", "mail.activity.mixin", "social.post.mixin"]
    _description = "Social Post"

    account_ids = fields.Many2many("social.account", required=True, ondelete="restrict")
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        required=True,
        index=True,
        default=lambda self: self.env.user,
        tracking=True,
        help="User this post belongs to. Only the responsible user and the "
        "social media administrators can see it.",
    )
    message = fields.Text(required=True, tracking=True)
    campaign_id = fields.Many2one("utm.campaign")
    allow_campaign_ids = fields.Many2many(
        "utm.campaign",
        relation="social_post_allow_campaign_rel",
        compute="_compute_allow_campaign_ids",
        help="Campaigns that can be linked to this post.",
    )
    send_post = fields.Selection(
        [("now", "Now"), ("schedule", "Schedule")],
        required=True,
        default="now",
        tracking=True,
    )
    send_post_date = fields.Datetime(
        string="Schedule date", compute="_compute_send_post_date", store=True
    )
    published_date = fields.Datetime(tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("planned", "Planned"),
            ("publishing", "Publishing"),
            ("published", "Published"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )
    post_account_ids = fields.One2many("social.post.account", "post_id")
    count_post_likes = fields.Integer(
        compute="_compute_post_statistics", default=0, string="Likes"
    )
    count_post_comments = fields.Integer(
        compute="_compute_post_statistics", default=0, string="Comments"
    )
    count_post_clicks = fields.Integer(
        compute="_compute_post_statistics", default=0, string="Clicks"
    )
    count_post_shares = fields.Integer(
        compute="_compute_post_statistics", default=0, string="Shares"
    )
    count_post_impression = fields.Integer(
        compute="_compute_post_statistics", default=0, string="Impression"
    )
    count_post_engagement = fields.Float(
        compute="_compute_post_statistics", default=0, string="Engagement"
    )
    count_post_interactions = fields.Float(
        compute="_compute_post_statistics", default=0, string="Interactions"
    )
    image_ids = fields.Many2many(
        "ir.attachment",
        column1="post_id",
        column2="image_id",
        ondelete="restrict",
        relation="social_network_post_image_rel",
    )
    video_ids = fields.Many2many(
        "ir.attachment",
        relation="social_network_post_video_rel",
        column1="post_id",
        column2="video_id",
        ondelete="restrict",
    )
    post_preview = fields.Html(compute="_compute_post_preview", store=True)
    message_info = fields.Text(compute="_compute_message_info")
    any_failed_post = fields.Boolean(compute="_compute_any_failed_post")
    hide_post = fields.Boolean(compute="_compute_hide_post")

    def _get_allow_campaign_domain(self):
        """Return the domain of the campaigns that can be linked to this post.

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

    @api.depends("account_ids")
    def _compute_allow_campaign_ids(self):
        UtmCampaign = self.env["utm.campaign"]
        for post in self:
            post.allow_campaign_ids = [
                Command.set(UtmCampaign.search(post._get_allow_campaign_domain()).ids)
            ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("send_post", False) == "schedule":
                vals["state"] = "planned"
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "send_post" in vals or "send_post_date" in vals:
            to_plan = self.filtered(
                lambda post: ("send_post" in vals and vals["send_post"] == "schedule")
                or ("send_post_date" in vals and post.send_post == "schedule")
            )
            if to_plan:
                to_plan.state = "planned"
        return res

    @api.depends("state", "any_failed_post", "send_post", "message", "account_ids")
    def _compute_hide_post(self):
        for post in self:
            post.hide_post = (
                (
                    post.state in ("planned", "publishing", "published", "cancelled")
                    and not post.any_failed_post
                )
                or not post.message
                or not post.account_ids
            )

    @api.depends("post_account_ids")
    def _compute_any_failed_post(self):
        for post in self:
            post.any_failed_post = any(
                post_account.state == "failed" for post_account in post.post_account_ids
            ) or (post.state == "publishing" and not post.post_account_ids)

    @api.depends("account_ids")
    def _compute_message_info(self):
        """Default when no social media module overrides this compute."""
        self.message_info = False

    @api.depends("account_ids.media_id")
    def _compute_display_name(self):
        for post in self:
            post.display_name = self.env._(
                "Post on %(posts)s",
                posts=", ".join(post.account_ids.mapped("media_id.name")),
            )

    @api.depends("send_post")
    def _compute_send_post_date(self):
        for post in self:
            if post.send_post == "schedule":
                post.send_post_date = fields.Datetime.now() + timedelta(hours=1)
            else:
                post.send_post_date = None

    @api.depends(
        "post_account_ids.like_count",
        "post_account_ids.comment_count",
        "post_account_ids.click_count",
        "post_account_ids.share_count",
        "post_account_ids.engagement",
        "post_account_ids.impression_count",
    )
    def _compute_post_statistics(self):
        for post in self:
            post.count_post_clicks = sum(post.mapped("post_account_ids.click_count"))
            post.count_post_shares = sum(post.mapped("post_account_ids.share_count"))
            post.count_post_likes = sum(post.mapped("post_account_ids.like_count"))
            post.count_post_engagement = sum(post.mapped("post_account_ids.engagement"))
            post.count_post_impression = sum(
                post.mapped("post_account_ids.impression_count")
            )
            post.count_post_comments = sum(
                post.mapped("post_account_ids.comment_count")
            )
            post.count_post_interactions = (
                post.count_post_clicks
                + post.count_post_likes
                + post.count_post_comments
                + post.count_post_shares
            )

    def filter_by_media_types(self, media_types, add_domain=None):
        domain = [
            ("media_type", "in", media_types),
            ("post_id", "=", self.id),
            ("state", "in", ("ready", "failed")),
        ]
        if add_domain:
            domain += add_domain
        return self.env["social.post.account"].search(domain)

    def action_draft(self):
        for post in self:
            post.state = "draft"

    def action_cancel(self):
        for post in self:
            if post.state in ("publishing", "published"):
                raise UserError(
                    self.env._(
                        "%(post)s: cannot be cancelled because it "
                        "is published or in the process of being published.",
                        post=post.display_name,
                    )
                )
            post.state = "cancelled"

    def _render_values_preview(self):
        """Return the extra rendering values of the preview.

        :rtype: dict
        """
        return {}

    def _render_template_preview(self):
        """Render one preview template per account of the post.

        :rtype: str
        """
        render_template = ""
        IrQweb = self.env["ir.qweb"]
        for account in self.account_ids:
            values = {
                "media_id": account.media_id,
                "author": account.name,
                "message": self.message,
                "image_ids": self.image_ids[0:2],
            }
            try:
                render_template += """\n\n""" + IrQweb._render(
                    f"social_media_{account.media_id.media_type}"
                    ".social_media_post_preview",
                    values | self._render_values_preview(),
                )
            except (ValueError, MissingError):
                render_template += """\n\n""" + IrQweb._render(
                    "social_media_base.social_media_post_preview",
                    values | self._render_values_preview(),
                )
        return (
            render_template if render_template else self.env._("No preview available")
        )

    @api.depends("account_ids", "message", "image_ids", "video_ids")
    def _compute_post_preview(self):
        """Render the preview of the post, one template per selected media.

        Templates are looked up as
        ``social_media_{media_type}.social_media_post_preview``, falling
        back to the generic one of this module.
        """
        for post in self:
            post.post_preview = post._render_template_preview()

    def _default_account_ids(self):
        """Return the account ids preselected when creating a post.

        :rtype: list
        """
        return []

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        account_ids = self._default_account_ids()
        if account_ids:
            res["account_ids"] = [(6, 0, account_ids)]
        return res

    def action_create_post_account(self):
        """Publish the post on all its social media accounts."""
        self._action_create_post_account()

    def _prepare_post_account_values(self):
        """Return the ``social.post.account`` commands, one per account.

        :rtype: list
        """
        posts_account = []
        for account in self.account_ids:
            if account.id not in self.post_account_ids.mapped("account_id").ids:
                posts_account.append(
                    Command.create(
                        {
                            "post_id": self.id,
                            "account_id": account.id,
                            "state": "ready",
                            "message": self.message,
                        }
                    )
                )
        return posts_account

    def _action_create_post_account(self):
        """Send the posts to the social networks and update their state."""
        SocialPostAccount = self.env["social.post.account"]
        for post in self:
            post.write(
                {
                    "state": "publishing",
                    "post_account_ids": post._prepare_post_account_values(),
                }
            )
            SocialPostAccount._action_post(post_id=post)
            if all(post_acc.state == "posted" for post_acc in post.post_account_ids):
                post.write({"state": "published"})
            elif all(post_acc.state == "failed" for post_acc in post.post_account_ids):
                post.write({"state": "draft"})

    def _message_error_post(self, message, media_id):
        self.message_post(
            body=self.env._(
                "Error posting on [%(media)s]: %(error)s",
                media=media_id,
                error=message,
            ),
        )

    def _run_send_post(self):
        """Send the posts whose scheduled date has been reached."""
        posts = self.env["social.post"].search(
            [
                ("state", "in", ("planned", "publishing")),
                ("send_post", "=", "schedule"),
                ("send_post_date", "<=", fields.Datetime.now()),
            ]
        )
        posts.with_context(social_post_cron=True)._action_create_post_account()
