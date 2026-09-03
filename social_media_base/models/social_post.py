# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_datetime

_logger = logging.getLogger(__name__)

PREVIEW_MEDIA_LIMIT = 2

LOCKED_CONTENT_FIELDS = (
    "account_ids",
    "message",
    "image_ids",
    "video_ids",
    "send_post",
    "send_post_date",
    "campaign_id",
)


class SocialPost(models.Model):
    """Content written once and published on several social accounts.

    Sending it fans the post out into one ``social.post.account`` per
    selected account, which is where the publication on each social media
    actually lives. This record only holds the editorial content and the
    overall state of that fan-out.
    """

    _name = "social.post"
    _inherit = ["mail.thread", "mail.activity.mixin", "social.post.mixin"]
    _description = "Content to Publish on Social Media"

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
    campaign_id = fields.Many2one(
        "utm.campaign",
        string="Campaign",
        index="btree_not_null",
        ondelete="set null",
    )
    send_post = fields.Selection(
        [("now", "Now"), ("schedule", "Schedule")],
        required=True,
        default="now",
        tracking=True,
    )
    send_post_date = fields.Datetime(
        string="Schedule date",
        compute="_compute_send_post_date",
        store=True,
        readonly=False,
        help="Date the post is sent to the social media. Switching to "
        "'Schedule' proposes one hour from now, and it can be changed.",
    )
    published_date = fields.Datetime(tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("planned", "Planned"),
            ("publishing", "Publishing"),
            ("partially_published", "Partially Published"),
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
    count_post_interactions = fields.Integer(
        compute="_compute_post_statistics", default=0, string="Interactions"
    )
    link_click_count = fields.Integer(
        string="Tracked Clicks",
        compute="_compute_link_click_count",
        help="Clicks Odoo registered on the tracked links of the publications "
        "of this post. Different from 'Clicks', which is the figure the "
        "social media report.",
    )
    image_ids = fields.Many2many(
        "ir.attachment",
        column1="post_id",
        column2="image_id",
        ondelete="restrict",
        relation="social_post_image_rel",
    )
    video_ids = fields.Many2many(
        "ir.attachment",
        relation="social_post_video_rel",
        column1="post_id",
        column2="video_id",
        ondelete="restrict",
    )
    post_preview = fields.Html(compute="_compute_post_preview", store=True)
    message_info = fields.Text(
        compute="_compute_post_check_messages",
        help="What a social media of the post is going to publish differently "
        "from what is written here. It does not stop anything: the post is "
        "published, changed by the social media.",
    )
    message_error = fields.Text(
        compute="_compute_post_check_messages",
        help="What no social media of the post will be able to publish as the "
        "post stands. It does not block saving, so the post can be finished "
        "later, but the publication is refused until it is fixed.",
    )
    any_failed_post = fields.Boolean(compute="_compute_any_failed_post")
    hide_post = fields.Boolean(compute="_compute_hide_post")
    content_locked = fields.Boolean(
        compute="_compute_content_locked",
        help="The post reached at least one social media, so what it says "
        "can no longer be changed.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("send_post", False) == "schedule":
                vals["state"] = "planned"
        return super().create(vals_list)

    def write(self, vals):
        self._check_content_not_locked(vals)
        to_toggle = (
            self.filtered(lambda post: post.active != vals["active"])
            if "active" in vals
            else self.browse()
        )
        res = super().write(vals)
        if to_toggle:
            lines = to_toggle.with_context(active_test=False).post_account_ids
            if vals["active"]:
                lines = lines.filtered(lambda line: line.account_id.active)
            lines.filtered(lambda line: line.active != vals["active"]).write(
                {"active": vals["active"]}
            )
            if vals["active"]:
                to_toggle._reset_overdue_schedule()
        if "send_post" in vals or "send_post_date" in vals:
            to_plan = self.filtered(
                lambda post: ("send_post" in vals and vals["send_post"] == "schedule")
                or ("send_post_date" in vals and post.send_post == "schedule")
            )
            if to_plan:
                to_plan.state = "planned"
        return res

    def unlink(self):
        """Delete the posts together with the publications they created.

        ``social.post.account.post_id`` is ``restrict`` on purpose, so that
        the history of what exists on the social media is never dropped by
        accident. The post is what knows whether that is the case: a
        publication that never reached the social media, or one already gone from
        it, is deleted with its post; a publication still online stops the
        deletion with an explanation.
        """
        lines = self.with_context(active_test=False).post_account_ids
        online = lines.filtered(
            lambda line: line.remote_ref and line.state != "deleted"
        )
        if online:
            raise UserError(
                _(
                    "The post %(posts)s cannot be deleted because it is still "
                    "published on %(accounts)s. Delete the publication from "
                    "the dashboard, which removes it from the social media "
                    "as well, or archive the post to keep its history.",
                    posts=", ".join(online.post_id.mapped("display_name")),
                    accounts=", ".join(online.account_id.mapped("display_name")),
                )
            )
        lines.unlink()
        return super().unlink()

    def _get_locked_content_fields(self):
        """Return the fields frozen once the post reached a social media.

        Extension point for the modules adding a field that changes what is
        published or how.

        :rtype: tuple
        """
        return LOCKED_CONTENT_FIELDS

    def _check_content_not_locked(self, vals):
        """Refuse to change what has already been sent to a social media.

        The publication is irreversible: once an account has published, the
        post is the description of something that exists outside of Odoo, and
        editing it would only make the two disagree. The form already shows
        those fields as readonly, so this guards the ways in that do not go
        through it, and the post that comes back to ``draft`` by any route
        while one of its publications is still online.

        :param vals: the values about to be written.
        """
        if not any(field in vals for field in self._get_locked_content_fields()):
            return
        locked = self.filtered("content_locked")
        if locked:
            raise UserError(
                _(
                    "%(posts)s cannot be modified because it is already "
                    "published on %(accounts)s. Create a new post instead.",
                    posts=", ".join(locked.mapped("display_name")),
                    accounts=", ".join(
                        locked._get_published_lines().account_id.mapped("display_name")
                    ),
                )
            )

    def _get_published_lines(self):
        """Return the publications of these posts that reached a social media.

        Archived publications count: they describe something that is still
        online, and archiving the post never removed it from the social media.

        :rtype: odoo.models.Model
        """
        return self.with_context(active_test=False).post_account_ids.filtered(
            lambda line: line.remote_ref or line.state == "posted"
        )

    @api.depends("post_account_ids.remote_ref", "post_account_ids.state")
    def _compute_content_locked(self):
        for post in self:
            post.content_locked = bool(post._get_published_lines())

    @api.constrains("send_post", "send_post_date")
    def _check_send_post_date_not_past(self):
        """Refuse to schedule a post for a date already reached.

        The cron sends every planned post whose date is past, so a date behind
        the clock is not a schedule: it is an immediate publication that
        nobody asked for. Only the states where the date is still a decision
        are checked, so a post already sent keeps the date it was sent on.
        """
        now = fields.Datetime.now()
        for post in self:
            if (
                post.send_post == "schedule"
                and post.state in ("draft", "planned")
                and post.send_post_date
                and post.send_post_date < now
            ):
                raise ValidationError(
                    _(
                        "The schedule date of %(post)s (%(date)s) is already "
                        "past. Choose a date in the future to plan the post.",
                        post=post.display_name,
                        date=format_datetime(self.env, post.send_post_date),
                    )
                )

    @api.constrains("image_ids", "video_ids")
    def _check_media_kind(self):
        """Refuse a file that is not of the kind of the field carrying it.

        Which formats a social media publishes is the business of its
        connector and is checked before publishing. This only keeps a video
        out of the images and an image out of the videos, which no social
        media accepts and which the file dialog does not enforce: its accepted
        extensions filter what the browser proposes, not what a drag and drop
        or an RPC call adds.
        """
        for post in self:
            for attachment in post.image_ids:
                if not (attachment.mimetype or "").startswith("image/"):
                    raise ValidationError(
                        _(
                            "%(name)s (%(mimetype)s) is not an image and cannot "
                            "be added to the images of the post.",
                            name=attachment.name,
                            mimetype=attachment.mimetype,
                        )
                    )
            for attachment in post.video_ids:
                if not (attachment.mimetype or "").startswith("video/"):
                    raise ValidationError(
                        _(
                            "%(name)s (%(mimetype)s) is not a video and cannot "
                            "be added to the videos of the post.",
                            name=attachment.name,
                            mimetype=attachment.mimetype,
                        )
                    )

    @api.depends("state", "any_failed_post", "send_post", "message", "account_ids")
    def _compute_hide_post(self):
        """Hide the post button when publishing is not a decision to take.

        A planned post keeps the button: the schedule says when the cron will
        send it, not that the user gave up on sending it right away. Once the
        post left for the social media the button only comes back to retry the
        publications that failed.
        """
        for post in self:
            post.hide_post = (
                (
                    post.state
                    in (
                        "publishing",
                        "partially_published",
                        "published",
                        "cancelled",
                    )
                    and not post.any_failed_post
                )
                or not post.message
                or not post.account_ids
            )

    @api.depends("state", "post_account_ids", "post_account_ids.state")
    def _compute_any_failed_post(self):
        for post in self:
            post.any_failed_post = any(
                post_account.state == "failed" for post_account in post.post_account_ids
            ) or (post.state == "publishing" and not post.post_account_ids)

    def _get_post_errors(self, media_type, account=None):
        """Return what stops this post from being published on a social media.

        Extension point: a connector overrides it, calls ``super()`` and
        appends its own reasons for its own ``media_type``. Everything
        returned here stops the publication on that social media, so a rule
        the media works around on its own belongs in
        :meth:`_get_post_warnings` instead.

        Most of what a social media refuses is a limit of the network, the
        same for every account, and is answered without ``account``: that is
        how the form asks, once per social media of the post. A rule that is
        really about one account — a feature its plan does not include, an
        advertising account it has not chosen — is answered only when the
        publication asks, so that it fails that publication alone.

        :param str media_type: the social media the post is checked against.
        :param account: the ``social.account`` about to publish, when the
            question is asked for one account instead of for the social media.
        :rtype: list
        """
        self.ensure_one()
        return []

    def _get_post_warnings(self, media_type, account=None):
        """Return what a social media will do differently with this post.

        Same contract as :meth:`_get_post_errors`, for what never stops the
        publication: LinkedIn publishing only the video of a post that also
        carries images is the post going out incomplete, not the post failing.

        :param str media_type: the social media the post is checked against.
        :param account: the ``social.account`` the warnings are asked for,
            when they are asked for one account instead of for the social
            media.
        :rtype: list
        """
        self.ensure_one()
        return []

    @api.depends("account_ids", "message", "image_ids", "video_ids")
    def _compute_post_check_messages(self):
        """Show what each social media of the post will refuse or change.

        Saving is never blocked: a post is written before it is finished, and
        the account that raises the objection may well be removed from it a
        moment later. The publication is where an error stops something.

        The social media are walked in a fixed order so that the block does
        not reshuffle itself between two recomputations of the same post.
        An account whose social media declares no ``media_type`` has no
        connector behind it, so there is nothing to ask about it.
        """
        for post in self:
            errors, warnings = [], []
            media_types = set(post.account_ids.mapped("media_type")) - {False}
            for media_type in sorted(media_types):
                errors += post._get_post_errors(media_type)
                warnings += post._get_post_warnings(media_type)
            post.message_error = "\n".join(errors) or False
            post.message_info = "\n".join(warnings) or False

    @api.depends("account_ids.media_id")
    def _compute_display_name(self):
        for post in self:
            post.display_name = _(
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
        "post_account_ids.interactions_count",
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
            post.count_post_interactions = sum(
                post.mapped("post_account_ids.interactions_count")
            )

    def _compute_link_click_count(self):
        """Count the clicks Odoo registered on the links of the publications.

        Never stored: nothing is written on the post, so an anonymous visit to
        a tracked link cannot turn into an UPDATE on its row, and the figures
        the social media report cannot overwrite it nor race with it. Same
        reason as in ``social.post.account._compute_link_click_count``.
        """
        counts = {
            post_account.id: count
            for post_account, count in self.env["link.tracker.click"]._read_group(
                [("social_post_account_id", "in", self.post_account_ids.ids)],
                ["social_post_account_id"],
                ["__count"],
            )
        }
        for post in self:
            post.link_click_count = sum(
                counts.get(post_account.id, 0) for post_account in post.post_account_ids
            )

    def _filter_by_media_types(self, media_types, add_domain=None):
        """Return the publications of this post that a connector has to send.

        Connectors call it to narrow the publications down to their own media
        and to the states that are still pending.

        :param list media_types: the ``media_type`` values to keep.
        :param list add_domain: extra leaves appended to the domain.
        :rtype: recordset of ``social.post.account``
        """
        self.ensure_one()
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
            if post.state in ("publishing", "partially_published", "published"):
                raise UserError(
                    _(
                        "%(post)s: cannot be cancelled because it "
                        "is published or in the process of being published.",
                        post=post.display_name,
                    )
                )
            post.state = "cancelled"

    def _medias_for_publication(self):
        """Return the images and the videos in the order the user added them.

        See :meth:`~odoo.addons.social_media_base.models.social_post_mixin.
        SocialPostMixin._sorted_medias` for why the order has to be forced.

        :rtype: tuple
        """
        self.ensure_one()
        return self._sorted_medias(self.image_ids), self._sorted_medias(self.video_ids)

    def _render_values_preview(self, media):
        """Return the extra rendering values of the preview of one media.

        Connector modules override it to make the preview match what their
        social media really publishes, which is why they receive the
        media: a post may target several media at once, and what one of
        them drops the others may publish.

        :param media: the ``social.media`` the preview is rendered for.
        :rtype: dict
        """
        return {}

    def _render_template_preview(self):
        """Render one preview template per media of the post.

        The preview answers how the content will look on a social media, not on a
        given account: the message and the attachments belong to the post, so
        several accounts of the same media would render the very same card.

        Only the first medias are drawn, and the template is told how many are
        left so the card says it, like the kanban one does.

        :rtype: str
        """
        render_template = ""
        IrQweb = self.env["ir.qweb"]
        images, videos = self._medias_for_publication()
        for media in self.account_ids.media_id:
            values = {
                "media_id": media,
                "author": media.name,
                "message": self.message,
                "image_ids": images[0:PREVIEW_MEDIA_LIMIT],
                "video_ids": videos[0:PREVIEW_MEDIA_LIMIT],
                "hidden_image_count": max(len(images) - PREVIEW_MEDIA_LIMIT, 0),
                "hidden_video_count": max(len(videos) - PREVIEW_MEDIA_LIMIT, 0),
            }
            values |= self._render_values_preview(media)
            try:
                render_template += """\n\n""" + IrQweb._render(
                    f"social_media_{media.media_type}.social_media_post_preview",
                    values,
                )
            except ValueError:
                render_template += """\n\n""" + IrQweb._render(
                    "social_media_base.social_media_post_preview",
                    values,
                )
        return render_template if render_template else _("No preview available")

    @api.depends("account_ids.media_id", "message", "image_ids", "video_ids")
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
            res["account_ids"] = [Command.set(account_ids)]
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

    def _sync_pending_lines_message(self):
        """Prepare the message of the publications that are about to be sent.

        The message of a publication is a copy taken when the line is created,
        and the line is only created once per account: without this, correcting
        the text of a post that failed everywhere would change what the user
        reads in Odoo and not what is sent to the social media, while the
        images, read from the post itself, would be updated. Nothing is
        copied once a publication is online: what it says is already public,
        and the whole post is frozen by then.

        The links are tracked outside that condition on purpose: a failed
        publication of an already published post is retried with its frozen
        content, and its links have to be tracked too. This is also the single
        call site right before the publications reach the social media, so it
        is where the links are converted whatever the order the connector
        modules are loaded in.
        """
        self.ensure_one()
        pending = self.post_account_ids.filtered(
            lambda line: line.state in ("ready", "failed")
        )
        if not self.content_locked:
            outdated = pending.filtered(lambda line: line.message != self.message)
            if outdated:
                outdated.write({"message": self.message})
        pending._shorten_message_links()

    def _action_create_post_account(self):
        """Send the posts to the social media and update their state."""
        SocialPostAccount = self.env["social.post.account"]
        for post in self:
            if not post.account_ids:
                raise UserError(
                    _(
                        "%(post)s has no active account: restore the account "
                        "before publishing it.",
                        post=post.display_name,
                    )
                )
            post.write(
                {
                    "state": "publishing",
                    "post_account_ids": post._prepare_post_account_values(),
                }
            )
            post._sync_pending_lines_message()
            SocialPostAccount._action_post(post_id=post)
            post._close_publication()

    def _close_publication(self):
        """Set the state of the post from the result of its publications.

        A publication that reached the social media cannot be taken back, so
        a partial success is an outcome of its own: the post is neither
        published nor pending, it is ``partially_published``. That state is
        out of the domain of :meth:`_run_send_post` on purpose, so the failed
        accounts are only retried when somebody presses the button again,
        instead of every five minutes forever. The post only goes back to
        ``draft``, where it can be corrected, when nothing at all was sent.
        """
        self.ensure_one()
        lines = self.post_account_ids
        if lines and all(line.state == "posted" for line in lines):
            self.write(
                {
                    "state": "published",
                    "published_date": fields.Datetime.now(),
                }
            )
        elif any(line.state == "posted" for line in lines):
            values = {"state": "partially_published"}
            if not self.published_date:
                values["published_date"] = fields.Datetime.now()
            self.write(values)
            self._notify_partial_publication(
                lines.filtered(lambda line: line.state == "failed")
            )
        elif lines and all(line.state == "failed" for line in lines):
            self.write({"state": "draft"})

    def _notify_partial_publication(self, failed_lines):
        """Tell the users in charge of the accounts that did not publish.

        The post is already online somewhere, so the failure is not going to
        be noticed by whoever opens the post next: the responsible of each
        account that failed is notified on the chatter, where the reason of
        every failure has already been logged by
        :meth:`~odoo.addons.social_media_base.models.social_post_account.
        SocialPostAccount._register_publish_failure`.

        :param failed_lines: the ``social.post.account`` that failed.
        """
        self.ensure_one()
        if not failed_lines:
            return
        partners = failed_lines.account_id.user_id.partner_id
        self.message_post(
            body=_(
                "The post was published on %(published)s but failed on "
                "%(failed)s. It is not sent again automatically: solve the "
                "problem and press Post to retry the accounts that failed.",
                published=", ".join(
                    self.post_account_ids.filtered(
                        lambda line: line.state == "posted"
                    ).account_id.mapped("display_name")
                ),
                failed=", ".join(failed_lines.account_id.mapped("display_name")),
            ),
            partner_ids=partners.ids,
        )

    def _message_error_post(self, message, media_type):
        self.message_post(
            body=_(
                "Error posting on [%(media)s]: %(error)s",
                media=media_type,
                error=message,
            ),
        )

    def _register_cron_failure(self, error, back_to_draft=False):
        """Leave in the chatter the reason why the cron could not send a post.

        The failure already rolled back its savepoint, so the note is the only
        trace the responsible user gets. A business error is not going to solve
        itself on the next run: the post goes back to draft, out of the reach
        of the cron, instead of failing every five minutes. Anything else keeps
        the post planned so the cron retries it.
        """
        self.ensure_one()
        try:
            if back_to_draft:
                self.write({"state": "draft"})
                body = _(
                    "The scheduled publication failed and the post was set "
                    "back to draft: %(error)s",
                    error=str(error),
                )
            else:
                body = _(
                    "The scheduled publication failed, the post stays planned "
                    "and will be retried: %(error)s",
                    error=str(error),
                )
            self.message_post(body=body)
        except Exception:  # noqa: BLE001 - the note must not drop the batch
            _logger.exception(
                "Could not record the failure of the scheduled post %s",
                self.display_name,
            )

    def _reset_overdue_schedule(self):
        """Send back to draft the posts whose scheduled date is already past.

        Called when a post becomes active again: while it was archived the
        cron could not see it, and reactivating it as ``planned`` with a date
        already reached would publish it on the social media within the
        next run, without anybody asking for it. Back in draft, the user
        reschedules it and posts it again deliberately.

        A ``partially_published`` post is left alone: it is already out of the
        reach of the cron, and its content cannot be edited anymore.
        """
        overdue = self.filtered(
            lambda post: post.state in ("planned", "publishing")
            and post.send_post == "schedule"
            and post.send_post_date
            and post.send_post_date <= fields.Datetime.now()
        )
        if not overdue:
            return
        overdue.write({"state": "draft"})
        for post in overdue:
            post.message_post(
                body=_(
                    "The post was set back to draft: its scheduled date "
                    "(%(date)s) had already passed when it was unarchived. "
                    "Reschedule it to publish it.",
                    date=fields.Datetime.to_string(post.send_post_date),
                )
            )

    @api.model
    def _run_send_post(self):
        """Send the posts whose scheduled date has been reached.

        The cron record does not set a user, so it runs as the one who
        installed the module: the search needs ``sudo()`` to see the posts of
        every responsible. Each post is then published on behalf of its own
        responsible, and isolated in its own savepoint so a failure outside
        the per-account guard does not drop the rest of the batch.

        ``partially_published`` is deliberately out of the domain: a post that
        already reached a social media is only retried by hand, otherwise a
        permanently failing account would be retried on every run.
        """
        posts = (
            self.env["social.post"]
            .sudo()
            .search(
                [
                    ("state", "in", ("planned", "publishing")),
                    ("send_post", "=", "schedule"),
                    ("send_post_date", "<=", fields.Datetime.now()),
                ]
            )
        )
        for post in posts:
            try:
                with self.env.cr.savepoint():
                    post.with_user(post.user_id).with_context(
                        **{
                            "social_post_cron": True,
                        }
                    )._action_create_post_account()
            except (UserError, ValidationError) as error:
                post._register_cron_failure(error, back_to_draft=True)
            except Exception as error:  # noqa: BLE001 - one post must not drop the batch
                _logger.exception(
                    "Error sending the scheduled post %s", post.display_name
                )
                post._register_cron_failure(error)
