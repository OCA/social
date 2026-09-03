# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging
import re
from contextlib import contextmanager

import psycopg2
import requests

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY
from odoo.tools import TEXT_URL_REGEX, plaintext2html

from ..exceptions import SocialCredentialsError

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    """Publication of a post on one social account.

    A ``social.post`` is the editorial content the user writes once. When it is
    sent, it fans out into one record of this model per selected account: this
    is the message as it actually exists on that social media, holding its
    remote identifier, its own publication state and the statistics the network
    reports back for that account.
    """

    _name = "social.post.account"
    _inherit = ["mail.thread", "social.post.mixin", "social.statistics.mixin"]
    _description = "Publication of a Post on a Social Account"
    _rec_name = "message"

    post_id = fields.Many2one("social.post", ondelete="restrict")
    active = fields.Boolean(default=True)
    account_id = fields.Many2one("social.account", ondelete="restrict", required=True)
    media_id = fields.Many2one(
        "social.media", related="account_id.media_id", required=True
    )
    media_type = fields.Selection(related="media_id.media_type")
    user_id = fields.Many2one(
        related="account_id.user_id",
        string="Responsible",
        store=True,
        index=True,
        readonly=True,
    )

    state = fields.Selection(
        [
            ("ready", "Ready"),
            ("posted", "Posted"),
            ("failed", "Failed"),
            ("deleted", "Deleted"),
        ],
        default="ready",
        help="'Deleted' means the publication no longer exists on the "
        "social media although it is kept in Odoo for history.",
    )
    published_date = fields.Datetime()
    effective_date = fields.Datetime(
        string="Date",
        compute="_compute_effective_date",
        store=True,
        help="Publication date, or the date the post is scheduled for while "
        "it is not published yet.",
    )
    is_scheduled = fields.Boolean(
        string="Scheduled",
        compute="_compute_is_scheduled",
        store=True,
        help="The post of this publication is scheduled and not published yet.",
    )
    message = fields.Text(required=True)
    remote_ref = fields.Char(
        string="Remote Reference",
        copy=False,
        index=True,
        help="Identifier of this publication on the social media. It is set "
        "by the connector module of each social media.",
    )
    account_remote_ref = fields.Char(
        related="account_id.remote_ref", string="Account Remote Reference"
    )

    engagement = fields.Float(default=0, digits=(16, 4))
    video_ids = fields.Many2many(
        "ir.attachment",
        relation="social_post_account_video_rel",
        column1="post_id",
        column2="video_id",
        ondelete="restrict",
    )

    image_ids = fields.Many2many(
        "ir.attachment",
        column1="post_id",
        column2="image_id",
        ondelete="restrict",
        relation="social_post_account_image_rel",
    )
    has_video = fields.Boolean(
        default=False,
        help="Indicates that the published post has at least one video attached.",
    )
    failed_description = fields.Html()
    post_account_url = fields.Char()
    author = fields.Char(related="account_id.name", store=True)
    actor_urn = fields.Char()
    campaign_id = fields.Many2one(
        "utm.campaign",
        string="Campaign",
        compute="_compute_campaign_id",
        store=True,
        readonly=False,
        index="btree_not_null",
        ondelete="set null",
        help="Marketing campaign of the parent post. A publication imported "
        "from the social media has no parent post, so its campaign is "
        "written on the imported publication itself.",
    )
    medium_id = fields.Many2one(
        "utm.medium",
        string="Medium",
        compute="_compute_medium_id",
        store=True,
        readonly=False,
        index="btree_not_null",
        ondelete="set null",
        help="Delivery method reported to the marketing campaign. It lives on "
        "the publication and not on the post because a post is spread over "
        "several social media.",
    )
    source_id = fields.Many2one(
        "utm.source",
        string="Source",
        readonly=True,
        copy=False,
        index="btree_not_null",
        ondelete="restrict",
        help="Created when the publication is sent, so that every publication "
        "of the same post owns its own tracked links.",
    )
    link_click_count = fields.Integer(
        string="Tracked Clicks",
        compute="_compute_link_click_count",
        help="Clicks Odoo registered on the tracked links of this "
        "publication. Different from 'Clicks', which is the figure the social "
        "media reports for the publication itself.",
    )

    @api.depends("published_date", "post_id.send_post_date")
    def _compute_effective_date(self):
        for post_account in self:
            post_account.effective_date = (
                post_account.published_date or post_account.post_id.send_post_date
            )

    @api.depends("published_date", "post_id.send_post_date")
    def _compute_is_scheduled(self):
        for post_account in self:
            post_account.is_scheduled = bool(
                post_account.post_id.send_post_date and not post_account.published_date
            )

    @api.depends("post_id.campaign_id")
    def _compute_campaign_id(self):
        """Propagate the marketing campaign of the parent post.

        Publications imported from the social media have no parent post:
        their campaign is written on the publication itself and must survive
        every recomputation, hence the filter.
        """
        for post_account in self.filtered("post_id"):
            post_account.campaign_id = post_account.post_id.campaign_id

    @api.constrains("campaign_id", "post_id")
    def _check_campaign_id(self):
        """A publication of a post always carries the campaign of that post.

        The marketing campaign decides how the publication is measured, so a
        publication cannot be moved to another campaign than the one of the
        post that produced it. Only a publication imported from the social
        media, which has no parent post, carries a campaign of its own.

        The field cannot simply be a related, which is what ``mailing.trace``
        does: a related traverses unconditionally, so a publication without a
        parent post would have its campaign wiped on every recomputation.
        """
        for post_account in self.filtered("post_id"):
            if post_account.campaign_id != post_account.post_id.campaign_id:
                raise ValidationError(
                    _(
                        "The campaign of a publication is the one of its "
                        "post. Change the campaign on %(post)s instead.",
                        post=post_account.post_id.display_name,
                    )
                )

    @api.depends("media_id", "media_id.utm_medium_id")
    def _compute_medium_id(self):
        """Report the delivery method of the social media of the publication."""
        for post_account in self:
            post_account.medium_id = post_account.media_id._get_utm_medium()

    def _compute_link_click_count(self):
        """Count the clicks Odoo registered on the links of the publication.

        Never stored: nothing is written on the publication, so the figures
        the social media report cannot overwrite it nor race with it.
        """
        counts = {
            post_account.id: count
            for post_account, count in self.env["link.tracker.click"]._read_group(
                [("social_post_account_id", "in", self.ids)],
                ["social_post_account_id"],
                ["__count"],
            )
        }
        for post_account in self:
            post_account.link_click_count = counts.get(post_account.id, 0)

    def _ensure_utm_source(self):
        """Give each publication its own UTM source, created on first use.

        The source is what tells the publications of a post apart: a link
        tracker is unique per url, campaign, medium and source, so without one
        source per publication every account would share a single tracker and
        a click could not be attributed to the account that published it.

        ``utm.source.mixin`` is not inherited on purpose: it makes the source
        required and adds a ``name`` related to it, while a publication is
        named after its message and the ones already in database have none.
        """
        UtmSource = self.env["utm.source"]
        for post_account in self.filtered(lambda line: not line.source_id):
            post_account.source_id = UtmSource.create(
                {"name": UtmSource._generate_name(post_account, post_account.message)}
            )

    def _get_link_tracker_title(self):
        """Return the title of the link trackers of this publication.

        Left alone, the link tracker names itself after the page it points to
        and falls back to the url itself, which says nothing about where a
        click came from and costs an outbound request while the post is being
        sent. A click is attributed to the publication, so the social media,
        the account and an excerpt of the message are what name the tracker.

        The links are dropped from the excerpt: they are the same information
        the url of the tracker already carries, and a message made of a single
        link would otherwise be named after it again. The excerpt is truncated
        the way ``utm.source`` truncates its own name, so the tracker and the
        source of the publication read alike.

        :rtype: str
        """
        self.ensure_one()
        content = re.sub(TEXT_URL_REGEX, "", self.message or "")
        content = " ".join(content.split())
        if len(content) >= 24:
            content = f"{content[:20]}..."
        if not content:
            return _(
                "[%(media)s] %(account)s",
                media=self.media_id.name,
                account=self.account_id.name,
            )
        return _(
            "[%(media)s] %(account)s - %(content)s",
            media=self.media_id.name,
            account=self.account_id.name,
            content=content,
        )

    def _get_link_tracker_values(self):
        """Return the values of the link trackers created for this publication.

        :rtype: dict
        """
        self.ensure_one()
        self._ensure_utm_source()
        return {
            "campaign_id": self.campaign_id.id,
            "medium_id": self.medium_id.id,
            "source_id": self.source_id.id,
            "social_post_account_id": self.id,
            "title": self._get_link_tracker_title(),
        }

    def _shorten_message_links(self):
        """Route the links of the message through the link tracker.

        The message is rewritten in place: what is stored is what was really
        published, the same way ``sms.sms`` keeps the body it sent.

        The links are shortened on the publication and not on the post because
        each publication carries its own UTM source, so the same link produces
        one tracker per account and a click can be attributed to the account
        that published it.

        Only a publication promoting a marketing campaign is tracked, and only
        when its message carries a link: tracking is what the campaign is
        measured with, and a publication without one has nothing to report.
        """
        MailRenderMixin = self.env["mail.render.mixin"]
        for post_account in self.filtered("campaign_id"):
            # The values create the UTM source of the publication, so they are
            # only asked for once the message is known to hold a link.
            if not re.search(TEXT_URL_REGEX, post_account.message or ""):
                continue
            message = MailRenderMixin._shorten_links_text(
                post_account.message, post_account._get_link_tracker_values()
            )
            if message != post_account.message:
                post_account.message = message

    def action_open_post_account_url(self):
        """Open this publication on the social media.

        The address is only known for a publication that made it to the social
        media, so the button showing it is hidden otherwise. Base opens it as
        it is: the address survives a deletion made on the social media, but
        finding that out costs a call per publication and is somebody else's
        job, which is what overrides this to ask first.
        """
        self.ensure_one()
        if not self.post_account_url:
            return False
        return {
            "type": "ir.actions.act_url",
            "url": self.post_account_url,
            "target": "new",
        }

    def _action_post(self, post_id):
        """Publish on the social media, implemented by each connector.

        :param post_id: the ``social.post`` being published.
        """

    def _check_publishable(self):
        """Refuse to publish what the social media is going to reject.

        Same source as the message the form shows while the post is edited,
        so the two can never disagree. It runs inside :meth:`_publish_guard`,
        so raising here fails this publication only.

        The account is passed on, unlike in the form, which asks once per
        social media: here there is one account and it is the one publishing,
        so a rule about that account alone stops that account alone.

        The warnings of :meth:`~odoo.addons.social_media_base.models.
        social_post.SocialPost._get_post_warnings` are not read here: by
        definition they do not stop a publication.

        :raise UserError: when the post cannot be published as it stands.
        """
        self.ensure_one()
        errors = self.post_id._get_post_errors(self.media_type, account=self.account_id)
        if errors:
            raise UserError("\n".join(errors))

    @contextmanager
    def _publish_guard(self):
        """Isolate the publication of one account in its own savepoint.

        Publishing is an irreversible external effect: once the social media
        has accepted the post, an error raised while publishing on another
        account must not roll back the reference of this one. Connectors wrap
        the body of their per-account loop with this guard so a failure is
        recorded on its own line, the accounts already published keep their
        ``remote_ref`` and the retry only targets the failed ones.
        """
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                yield
        except psycopg2.OperationalError as error:
            if error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                raise
            self._register_publish_failure(error)
        except Exception as error:  # noqa: BLE001 - external effect, see above
            self._register_publish_failure(error)

    def _publish_attempt(self, publish, **kwargs):
        """Publish, renewing the credentials of the account when needed.

        The token is renewed first when the connector knows from its stored
        dates that it expired, which is what the hook is for. Those dates
        cannot see a token revoked on the social media side, nor one that runs out
        between the check and the call: that only shows up as the social media
        refusing the credentials, and it means nothing was published, so the
        same call is safe to run a second time once the token has been
        renewed. Any other error is left alone: the social media is not going
        to change its mind about the content.

        Called from inside :meth:`_publish_guard`, so an account whose
        credentials cannot be renewed fails its own line, with the reason on
        it, and the other accounts of the post go out as usual.

        :param publish: the bound method that publishes on the social media.
        :param kwargs: the arguments of that method.
        :return: whatever ``publish`` returns.
        """
        self.ensure_one()
        self.account_id.with_context(not_notify=True).validate_access_token()
        try:
            return publish(**kwargs)
        except SocialCredentialsError as error:
            if not self.account_id._refresh_credentials():
                self.account_id._flag_credentials_expired(str(error))
                raise
            _logger.info(
                "Credentials renewed while publishing on %(media)s for account "
                "%(account)s, publishing again",
                {"media": self.media_type, "account": self.account_id.name},
            )
        return publish(**kwargs)

    def _register_publish_failure(self, error):
        """Mark this publication as failed and keep the reason on the line.

        Called from the ``except`` block of :meth:`_publish_guard`, once the
        savepoint has been rolled back and the ORM cache cleared.

        :param error: the exception raised while publishing.
        """
        _logger.exception(
            "Error publishing the post on %(media)s for account %(account)s",
            {"media": self.media_type, "account": self.account_id.name},
        )
        self.write(
            {
                "state": "failed",
                "failed_description": plaintext2html(str(error)),
            }
        )
        if self.post_id:
            self.post_id._message_error_post(str(error), self.media_type)

    def _delete_post_account(self):
        """Delete the publication on the social media.

        :return: ``success`` and ``message`` of the action.
        :rtype: dict
        """

    def _register_delete_failure(self, error):
        """Record that the remote publication is gone but the line survived.

        Called once the savepoint of :meth:`action_delete_post_account` has been
        rolled back. The social media has already deleted the publication at
        that point, so the line is kept as failed and without its remote
        reference, which is the truth, instead of raising and rolling back the
        whole transaction into a line pointing at something that no longer
        exists.

        :param error: the exception raised while deleting the local records.
        :return: a notification action describing what is left to do.
        :rtype: dict
        """
        _logger.exception(
            "The post was deleted on %(media)s for account %(account)s but "
            "its Odoo records could not be removed",
            {"media": self.media_type, "account": self.account_id.name},
        )
        self.write(
            {
                "remote_ref": False,
                "post_account_url": False,
                "state": "failed",
                "failed_description": plaintext2html(str(error)),
            }
        )
        if self.post_id:
            self.post_id._message_error_post(str(error), self.media_type)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Post deleted [%(account)s]", account=self.account_id.name),
                "type": "danger",
                "message": _(
                    "The post was deleted on the social media, but its Odoo "
                    "record could not be removed: %(error)s",
                    error=str(error),
                ),
                "sticky": True,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    def action_delete_post_account(self):
        self.ensure_one()
        self._delete_post_account()
        account_id = self.account_id
        post_id = self.post_id
        try:
            with self.env.cr.savepoint():
                self.unlink()
                if not post_id.post_account_ids:
                    post_id.unlink()
        except psycopg2.OperationalError as error:
            if error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                raise
            return self._register_delete_failure(error)
        except Exception as error:  # noqa: BLE001 - external effect, see above
            return self._register_delete_failure(error)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Post deleted [%(account)s]", account=account_id.name),
                "type": "success",
                "message": _("The post was successfully deleted."),
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    def action_open_statistics(self):
        """Open the figures of the publication in a dialog.

        Called from the menu of the card of the dashboard, which is where the
        figures brought by the synchronization were missing. Nothing is asked
        to the social media: what is shown is what the last update stored.

        :return: the action opening the statistics view.
        :rtype: dict
        """
        self.ensure_one()
        view = self.env.ref(
            "social_media_base.social_post_account_view_form_statistics"
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Statistics"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [(view.id, "form")],
            "target": "new",
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._anchor_media_attachments()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "image_ids" in vals or "video_ids" in vals:
            self._anchor_media_attachments()
        return res

    def _anchor_media_attachments(self):
        """Attach the downloaded medias to their publication.

        They are created together with it, so they end up with an empty
        ``res_id``: in that state only the administrators can read them and
        everybody else gets a placeholder instead of the image.
        """
        for post_account in self:
            attachments = (post_account.image_ids | post_account.video_ids).filtered(
                lambda attachment: not attachment.res_id
            )
            if attachments:
                attachments.sudo().write(
                    {"res_model": post_account._name, "res_id": post_account.id}
                )

    def _get_medias_account(self, medias):
        """Return the names of the medias already downloaded for this account.

        ``sudo()`` is needed to avoid downloading a media twice: a user who
        cannot read another user's attachments would otherwise duplicate
        every image on each synchronization.

        :rtype: list
        """
        if not medias:
            return []
        return (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("name", "in", medias),
                    ("res_model", "=", self._name),
                ]
            )
            .mapped("name")
        )

    def _map_medias_account(self, **values):
        """Download a media of the social media and attach it here.

        Nothing is created when the download fails: an attachment without
        ``datas`` would still take the name of the media, and
        :meth:`_get_medias_account` would then consider it already downloaded
        and never retry it.

        :return: the command creating the attachment, or False on failure.
        :rtype: dict | bool
        """
        attach_values = values or {}
        if not values.get("url", False):
            return Command.create(attach_values)
        try:
            media_content = requests.get(values["url"], timeout=10)
        except requests.exceptions.RequestException:
            _logger.warning("Could not download the media %s", values["url"])
            return False
        if media_content.status_code != 200:
            _logger.warning(
                "Could not download the media %(url)s: %(status)s",
                {"url": values["url"], "status": media_content.status_code},
            )
            return False
        attach_values.update(
            {
                "type": "binary",
                "res_model": self._name,
                "res_id": self.id,
                "datas": base64.b64encode(media_content.content),
            }
        )
        return Command.create(attach_values)

    def _copy_medias_account(self, attachments, names):
        """Copy the local attachments of the post into this publication.

        Used when the social media has not exposed the uploaded medias yet:
        the binary is already in Odoo, so it is copied instead of being
        downloaded back. Every copy takes the name of the media it became on
        the social media, so :meth:`_get_medias_account` recognises it and
        the next synchronization does not download a duplicate.

        :param attachments: the local attachments of the post.
        :param names: the remote names, in the same order as ``attachments``.
        :return: the commands creating the copies.
        :rtype: list
        """
        self.ensure_one()
        stored = self._get_medias_account(list(names))
        return [
            Command.create(
                {
                    "name": name,
                    "type": "binary",
                    "mimetype": attachment.mimetype,
                    "datas": attachment.datas,
                    "res_model": self._name,
                    "res_id": self.id,
                }
            )
            for attachment, name in zip(attachments, names, strict=False)
            if name and name not in stored
        ]
