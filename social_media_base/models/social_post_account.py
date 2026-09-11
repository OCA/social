# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import re
from contextlib import contextmanager

import psycopg2

from odoo import _, api, fields, models
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
    message = fields.Text(
        required=True,
        help="Text this publication sends to the social media, which is not "
        "the text of its post: every publication carries its own UTM source, "
        "so each link is rewritten into a tracker of its own and the same "
        "post reads differently on every account. "
        "Publications imported from the social media have no post to read a "
        "message from either.",
    )
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
    media_refs = fields.Json(
        copy=False,
        default=dict,
        help="Reference each media of this publication has on the social "
        "media, keyed by the identifier of its attachment. A media without "
        "an entry here is one the social media does not know about.",
    )
    failed_description = fields.Html()
    post_account_url = fields.Char()
    author = fields.Char(related="account_id.name", store=True)
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
    statistics_date = fields.Datetime(
        string="Statistics Read On",
        readonly=True,
        copy=False,
        help="When the figures of this publication were last read back from "
        "the social media. Empty means they were never read.",
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

    @api.constrains("media_refs", "image_ids", "video_ids")
    def _check_media_refs(self):
        """A publication never holds the same remote media twice.

        ``media_refs`` is what tells a media downloaded from the social media
        apart from one attached by hand, and it is what keeps a
        synchronization from storing an asset the publication already has.
        Two attachments pointing at the same remote reference would defeat
        both.

        A reference to the media of another publication is the other half of
        the same guarantee: it would make this one answer for a media it does
        not have. That is what is watched, and the reference is measured by
        what its attachment is anchored to.

        A reference to an attachment anchored nowhere, or still anchored to
        this very publication, points at nobody else and is left alone: it is
        what the retention of the downloaded medias leaves behind on purpose,
        so that they are not downloaded again. The attachment is released
        after the write that dropped the media, so it is still anchored here
        while this runs.
        """
        for post_account in self:
            refs = post_account.media_refs or {}
            if not refs:
                continue
            medias = post_account.image_ids | post_account.video_ids
            missing = set(refs) - {str(media.id) for media in medias}
            dangling = {
                str(attachment.id)
                for attachment in self.env["ir.attachment"]
                .sudo()
                .browse(int(ref) for ref in missing)
                .exists()
                if (attachment.res_model, attachment.res_id)
                != (self._name, post_account.id)
                and attachment.res_id
            }
            if dangling:
                raise ValidationError(
                    _(
                        "%(publication)s references medias it does not have: "
                        "%(medias)s.",
                        publication=post_account.display_name,
                        medias=", ".join(sorted(dangling)),
                    )
                )
            if len(set(refs.values())) != len(refs):
                raise ValidationError(
                    _(
                        "%(publication)s has the same media stored twice.",
                        publication=post_account.display_name,
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
        """Ask the social media, then open this publication on it.

        The address is only known for a publication that made it to the social
        media, so the button showing it is hidden otherwise. The address alone
        is not proof that the publication is still online: it survives a
        deletion made on the social media until something asks. Asking costs
        one call, for the one publication the user is opening, which is what
        makes it worth making here.
        """
        self.ensure_one()
        if not self.post_account_url:
            return False
        if not self.check_post_exists():
            return self._notify_remote_post_gone()
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

        The message the rules are measured against is the one of this
        publication and not the one of the post. The two differ once
        :meth:`_shorten_message_links` has replaced the links of a
        publication promoting a campaign by tracked ones, which are
        frequently longer than what the user wrote, so a post that fits the
        limit of the social media while it is being written can be over it by
        the time it goes out. It travels in the context because every
        connector reads it through
        :meth:`~odoo.addons.social_media_base.models.social_post.SocialPost.
        _get_checked_message`, whatever the order the modules extending the
        rules are loaded in.

        The warnings of :meth:`~odoo.addons.social_media_base.models.
        social_post.SocialPost._get_post_warnings` are not read here: by
        definition they do not stop a publication.

        :raise UserError: when the post cannot be published as it stands.
        """
        self.ensure_one()
        errors = self.post_id.with_context(
            social_checked_message=self.message
        )._get_post_errors(self.media_type, account=self.account_id)
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

    def _register_publish_success(self, remote_ref, url, media_refs, has_video):
        """Store what the social media answered for a publication of its own.

        Every connector writes the same line once its social media took the
        post; what differs is the reference, the URL it builds from it and
        what it made of the medias.

        :param remote_ref: identifier of the publication on the social media.
        :param url: address of that publication.
        :param media_refs: what the social media made of each media.
        :param bool has_video: whether a video was published.
        """
        self.ensure_one()
        self.write(
            {
                "remote_ref": remote_ref,
                "post_account_url": url,
                "media_refs": media_refs,
                "has_video": has_video,
                "state": "posted",
                "published_date": fields.Datetime.now(),
                "failed_description": False,
            }
        )

    def _register_publish_refused(self, message):
        """Mark the publication failed with what the connector has to say.

        The counterpart of :meth:`~._register_publish_success` for the answer
        that brought no reference back. It is not
        :meth:`~._register_publish_failure`: nothing was raised, the social
        media simply did not take the post.

        :param message: the reason shown on the line, as plain text.
        """
        self.ensure_one()
        self.write(
            {
                "state": "failed",
                "failed_description": plaintext2html(message),
            }
        )

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

    def check_post_exists(self):
        """Ask the social media whether this publication is still online.

        Public entry point shared by the form button and by the dashboard, so
        both answer the same thing from the same code.

        :rtype: bool
        """
        self.ensure_one()
        return self._check_remote_post_exists()

    def _check_remote_post_exists(self):
        """Whether the publication still exists, implemented by each connector.

        The contract is to fail open: ``False`` is only answered when the
        social media positively reported the publication as gone. A lost
        permission, a rate limit or a connection error must answer ``True`` and
        leave the record untouched, because a publication is not deleted just
        because Odoo could not read it.

        :rtype: bool
        """
        return bool(self.remote_ref)

    def _check_remote_posts_exist(self):
        """Which of these publications the social media reports as gone.

        The plural of :meth:`_check_remote_post_exists`, and it keeps its
        contract: a line is only answered when the social media positively
        reported the publication as gone. Anything else --a lost permission, a
        rate limit, a connection error-- leaves the line out of the answer,
        because a publication is not deleted just because Odoo could not read
        it. A check that raises resolves nothing about its own line and stops
        nothing about the others, which is why the loop asks for each of them
        on its own.

        It exists as a method of its own so a connector whose API answers a
        whole batch in one call --LinkedIn does, by ``ids``-- pays one call per
        hundred suspects instead of one per suspect. The default is the honest
        one: ask for each of them.

        :return: the lines the social media confirms are gone.
        :rtype: recordset
        """
        gone = self.browse()
        for line in self:
            try:
                if not line._check_remote_post_exists():
                    gone |= line
            except Exception:  # noqa: BLE001 - a failed check is not a deletion
                _logger.exception(
                    "Error checking whether the post %s still exists, it is "
                    "left untouched",
                    line.remote_ref,
                )
        return gone

    def _register_remote_post_gone(self):
        """Record that the publication no longer exists on the social media.

        ``remote_ref`` is kept on purpose: it is the only handle left on the
        publication, and detection is not infallible, so a line wrongly marked
        can be recognised and restored by the next full refresh.
        """
        self.write({"state": "deleted", "post_account_url": False})

    def _register_remote_posts_gone(self):
        """Mark as gone the publications the social media confirms are gone.

        The entry point for anything that marks in bulk. Missing from a listing
        is not proof: a feed read short, an index that has not caught up with
        what was published minutes ago, a kind of publication the finder does
        not answer --any of them makes a live publication look absent-- and
        marking it would take it out of every later pass, which read the live
        ones only.

        :return: the lines that were marked.
        :rtype: recordset
        """
        gone = self._check_remote_posts_exist()
        gone._register_remote_post_gone()
        return gone

    def _remote_post_gone_on_action(self):
        """Whether an action failed because the publication no longer exists.

        A ``404`` on a reaction or on a comment is not proof on its own: the
        social media answers the same for a reference it does not recognise or
        for a lost permission, and marking a live publication as deleted is
        worse than one extra request. The publication itself is asked about
        instead, which is also what registers the deletion once it is
        confirmed.

        The check runs from paths that are already handling a failure, so it
        answers ``False`` instead of raising: an action that could not be
        completed must report its own error, not the one of the check made
        to explain it.

        :rtype: bool
        """
        self.ensure_one()
        try:
            return not self._check_remote_post_exists()
        except Exception:  # noqa: BLE001 - a failed check is not a deletion
            _logger.exception(
                "Error checking whether the post %s still exists, it is left "
                "untouched",
                self.remote_ref,
            )
            return False

    def _notify_remote_post_gone(self):
        """Tell the user the publication is gone and refresh what is shown."""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Post deleted [%(account)s]", account=self.account_id.name),
                "type": "warning",
                "message": _("The post does not exist or has been deleted."),
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
        medias_touched = "image_ids" in vals or "video_ids" in vals
        released = (
            self._owned_media_attachments()
            if medias_touched
            else self.env["ir.attachment"]
        )
        res = super().write(vals)
        if medias_touched:
            self._anchor_media_attachments()
            self._release_media_attachments(released)
        return res

    def _media_attachments_to_skip(self):
        """The medias shared with the post belong to the post.

        The publication only owns what it downloaded from the social media
        itself.

        :rtype: recordset of ``ir.attachment``
        """
        self.ensure_one()
        return self.post_id.image_ids | self.post_id.video_ids
