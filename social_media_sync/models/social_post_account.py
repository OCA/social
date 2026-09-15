# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging
from datetime import datetime

import pytz
import requests

from odoo import Command, api, fields, models
from odoo.tools.misc import _format_time_ago

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    """What the publication reads back from its social media.

    Reading a thread costs one call per thread, and one more per thread of
    replies: a cost that grows with what the account has published, which is
    why it is not in ``social_media_base``. Asking whether one publication is
    still online costs a single call and stays there.
    """

    _inherit = "social.post.account"

    liked_by_account = fields.Boolean(
        string="Recommended",
        readonly=True,
        copy=False,
        help="Whether the account has a reaction of its own on this "
        "publication. It is what the Recommend entry of the dashboard "
        "toggles, and every import refreshes it from the social media.",
    )
    actor_urn = fields.Char(
        string="Author Reference",
        copy=False,
        help="Reference of the author of the publication on the social media, "
        "as the import read it. It is what the social media answers about "
        "whoever published, which is not always the account that imported it: "
        "a page publishes as the page and a person as the person.",
    )

    def action_like_post(self, author_urn=None):
        """Recommend the publication on the social media.

        :param author_urn: actor urn performing the reaction.
        :return: ``success`` and ``message`` of the action, plus
            ``post_deleted`` when the attempt is what revealed the publication
            is gone, so the client refreshes what it draws, and ``liked``,
            what the social media holds once the call is over --``None`` when
            it did not say, and then the client leaves the entry as it drew
            it.
        :rtype: dict
        """
        return {"success": True, "message": "", "post_deleted": False, "liked": True}

    def action_unlike_post(self, author_urn=None):
        """Withdraw the reaction of the account from the publication.

        The counterpart of :meth:`action_like_post`, and the reason the entry
        of the dashboard is a toggle instead of a one-way action.

        :param author_urn: actor urn whose reaction is withdrawn.
        :return: the same keys :meth:`action_like_post` answers.
        :rtype: dict
        """
        return {"success": True, "message": "", "post_deleted": False, "liked": False}

    def action_like_comment(self, comment_ref=None, author_urn=None):
        """Recommend a comment of the publication on the social media.

        :param comment_ref: reference of the comment on the social media, as
            ``get_comments`` answered it in ``remote_ref``.
        :param author_urn: actor urn performing the reaction.
        :return: the same keys :meth:`action_like_post` answers.
        :rtype: dict
        """
        return {"success": True, "message": "", "post_deleted": False, "liked": True}

    def action_unlike_comment(self, comment_ref=None, author_urn=None):
        """Withdraw the reaction of the account from a comment.

        :param comment_ref: reference of the comment on the social media, as
            ``get_comments`` answered it in ``remote_ref``.
        :param author_urn: actor urn whose reaction is withdrawn.
        :return: the same keys :meth:`action_like_post` answers.
        :rtype: dict
        """
        return {"success": True, "message": "", "post_deleted": False, "liked": False}

    def get_comments(self):
        """Retrieve the comments of the publication.

        Every element of ``data`` is a comment as the client draws it::

            {
                "id": "7491701601242423296",
                "remote_ref": "urn:li:comment:(urn:li:activity:749…,749…)",
                "parent_ref": False,
                "reply_count": None,
                "text": "Comment",
                "actor": "Acme Corporation",
                "author_image": "https://media.licdn.com/dms/image/…",
                "published_time": "2 weeks ago",
                "images_url": [],
                "liked": False,
            }

        ``remote_ref`` is what names the comment on the social media, and what
        travels back as the target of a reply. ``parent_ref`` is the
        ``remote_ref`` of the comment this one hangs from, ``False`` when it
        hangs from the publication itself. ``reply_count`` is how many replies
        it has, and ``None`` when the social media does not say without being
        asked for it — LinkedIn answers the comments of a post without any
        summary of their replies, so the count only arrives with
        ``get_comment_replies``.

        ``actor`` is a name to draw, never an identifier of the social media:
        a connector whose API answers only a reference resolves it before
        answering, and where it cannot --LinkedIn does not let a member be
        read-- it answers a neutral label of its own. The client draws what
        arrives, so an unresolved reference here would be shown to the user
        as it is. ``author_image`` is the URL of the picture of that actor,
        ``False`` or ``None`` when the social media reports none, and then
        the client draws a generic icon.

        ``published_time`` is the sentence :meth:`_format_published_time`
        builds, never a date: the client draws it as it arrives, so a
        connector answering the stamp of its own API would show the user a raw
        moment where every other social media says how long ago it was.

        ``liked`` is whether the account already reacted to the comment, which
        is what draws the *Recommend* entry as one thing or the other. A
        social media that does not say answers ``False``.

        :return: ``success`` and ``data`` of the action.
        :rtype: dict
        """
        return {"success": False, "data": []}

    def get_comment_replies(self, comment_ref):
        """Retrieve the replies of one comment, implemented by each connector.

        Only the connectors whose social media serves the replies apart need
        it: where the whole thread already arrives with ``get_comments``, the
        replies are nested from what is already on the client and this hook is
        never called.

        :param comment_ref: reference of the comment on the social media, as
            ``get_comments`` answered it in ``remote_ref``.
        :return: ``success``, ``data`` — the replies, shaped as the comments of
            ``get_comments`` — and ``count``, how many the social media says
            there are.
        :rtype: dict
        """
        return {"success": False, "data": [], "count": 0}

    def delete_comment(self, comment_ref):
        """Delete one comment of the thread, implemented by each connector.

        Only the connectors whose social media lets the owner of a
        publication moderate its thread need it. The client only offers the
        entry where ``canDeleteComment`` says so, so this answer is the one a
        call that should never have been made gets.

        :param comment_ref: reference of the comment on the social media, as
            ``get_comments`` answered it.
        :return: ``success`` and, on a failure, the ``message`` to show.
        :rtype: dict
        """
        return {"success": False}

    def create_comment(self, post_data, context=None):
        """Create a comment on the social media.

        A reply is created the same way a first-level comment is: the client
        puts the ``remote_ref`` of the comment being answered in
        ``post_data["social_parent_ref"]``, and the key is simply absent when
        the comment hangs from the publication.

        A connector that can shape what it just published answers it in
        ``comment``, as one element of the list :meth:`get_comments`
        documents. The client draws that one instead of reading the thread
        again, which is what keeps a published comment from costing a second
        call against the social media. The key is left out when the answer of
        the social media does not carry enough to shape it, and then the
        client falls back to rereading the thread.

        :param post_data: message and other data of the comment.
        :param context: optional context used to render the comment.
        :return: ``success`` and ``data`` of the action, ``comment`` when the
            published comment could be shaped, plus ``post_deleted`` when the
            attempt is what revealed the publication is gone.
        :rtype: dict
        """

    def _format_published_time(self, published):
        """Return how long ago a moment is, ready to be shown to the user.

        The comments and the publications the social media answer carry the
        moment they were written, and the client draws it as "3 days ago" next
        to each one. ``_format_time_ago`` wraps
        ``babel.dates.format_timedelta``, so the text comes out in the
        language of the user and with the direction a reader expects: "3 days
        ago" rather than "3 days". The core reads it the same way for the same
        purpose in ``addons/website/models/website_visitor.py``.

        A moment is what every connector hands over, whatever shape its API
        answers with: an epoch, a stamp with an offset or none at all is the
        connector's to convert, and what reaches the client is the same
        sentence for every social media. A value without a time zone is read
        as UTC, which is what those APIs answer and what Odoo stores, and the
        delta is taken against a UTC now so that the two ends of the
        subtraction are comparable.

        A moment the social media did not say answers nothing, and the client
        then draws the comment without a date instead of one written at the
        epoch.

        :param published: the moment the content was published, as a
            ``datetime``.
        :rtype: str
        """
        if not published:
            return ""
        if not published.tzinfo:
            published = pytz.utc.localize(published)
        return _format_time_ago(self.env, datetime.now(pytz.utc) - published)

    def _get_medias_account(self, medias):
        """Return which of ``medias`` this publication already holds.

        ``medias`` are references on the social media, and the answer comes
        from ``media_refs``: the question is whether this publication has
        that media, not whether some attachment of the database carries that
        name. Two publications of the same post therefore answer for
        themselves, even when the same image gave a different reference on
        each account.

        An empty recordset holds nothing, which is what the import asks
        about a publication it has not created yet.

        :rtype: list
        """
        if not self or not medias:
            return []
        self.ensure_one()
        stored = set((self.media_refs or {}).values())
        return [media for media in medias if media in stored]

    @api.model
    def _by_remote_ref(self, refs, account, sudo=False, active_test=True):
        """Index the publications of an account by their remote reference.

        Both bridges read the page the social media answered and have to tell
        which of its entries are already in Odoo. The reference alone does not
        tell: two accounts seeing the same publication — a company and a
        profile sharing it, or the same account associated twice — hold a line
        each for it, so the account is what says which of them the import is
        reconciling. It is a required parameter for that reason: a caller
        cannot forget what it does not choose to pass.

        The two flags say what is being reconciled, and both bridges answer
        the same: the archived publications count, and the lines are read past
        the record rules. Anything left out is imported again under a second
        line for the same publication, and the cron does not run as the user
        responsible for the account.

        A reference answers one publication of the account; the first one wins
        if a database ever holds two.

        :param refs: the remote references the social media answered.
        :param account: the ``social.account`` the page was read from.
        :param bool sudo: whether to read past the record rules.
        :param bool active_test: whether to leave the archived ones out.
        :rtype: dict
        """
        if not refs:
            return {}
        records = self.sudo() if sudo else self
        lines = records.with_context(active_test=active_test).search(
            [("remote_ref", "in", list(refs)), ("account_id", "=", account.id)]
        )
        return {ref: found[:1] for ref, found in lines.grouped("remote_ref").items()}

    def _store_remote_medias(self, url_by_ref):
        """Download the medias of a publication and keep what came back.

        The bridges arrive here having already left out what is stored and
        what the social media reported without a URL, so a media without one
        is skipped instead of asked for.

        The attachments come out in the order of the mapping, which is the
        order the social media listed them in: that is what the card draws.

        :param url_by_ref: ``{reference: url}``, the reference being the one
            the social media names the media by.
        :return: the attachments created and the reference of each one, keyed
            by its identifier. Both go into the same write, so that a
            downloaded media is never stored without the reference telling it
            apart from one attached in Odoo.
        :rtype: tuple
        """
        attachments = self.env["ir.attachment"]
        media_refs = {}
        for ref, url in url_by_ref.items():
            if not url:
                continue
            attachment = self._map_medias_account(name=ref, url=url)
            if attachment:
                attachments |= attachment
                media_refs[str(attachment.id)] = ref
        return attachments, media_refs

    def _map_medias_account(self, **values):
        """Download a media of the social media and attach it here.

        Nothing is created when the download fails, so that the publication
        is not left with an empty attachment the next synchronization has no
        reason to replace.

        The attachment is created here and not returned as a command, because
        its caller needs the identifier to key ``media_refs`` by it: nested in
        a command the identifier would only exist once the write it belongs to
        had run, and the reference would be lost.

        The ``url`` the media is downloaded from is required: the bridges
        skip a media the social media reported without one instead of asking
        for it here.

        :return: the attachment created, or an empty recordset on failure.
        :rtype: odoo.models.Model
        """
        Attachment = self.env["ir.attachment"]
        attach_values = values or {}
        try:
            media_content = requests.get(values["url"], timeout=10)
        except requests.exceptions.RequestException:
            _logger.warning("Could not download the media %s", values["url"])
            return Attachment
        if media_content.status_code != 200:
            _logger.warning(
                "Could not download the media %(url)s: %(status)s",
                {"url": values["url"], "status": media_content.status_code},
            )
            return Attachment
        attach_values.update(
            {
                "type": "binary",
                "res_model": self._name,
                "res_id": self.id,
                "datas": base64.b64encode(media_content.content),
            }
        )
        return Attachment.create(attach_values)

    def _media_retention_days(self):
        """Return for how many days the downloaded medias are kept.

        Zero is no policy at all, and it is what the module ships with: an
        ``Integer`` of ``res.config.settings`` cannot store a zero, so an
        administrator leaving the setting alone writes no parameter row, and
        no parameter row reads back as zero here.

        :rtype: int
        """
        days = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("social_media_sync.media_max_age_days", 0)
        )
        try:
            return int(days)
        except (TypeError, ValueError):
            _logger.warning(
                "The maximum age of the downloaded medias is not a number: %s",
                days,
            )
            return 0

    def _media_retention_domain(self, days):
        """Return which publications the retention policy reaches.

        Only the imported ones, which are the publications without a post:
        what a publication of a post carries are the medias of that post,
        editorial content that is never aged out.

        :param days: for how many days the downloaded medias are kept.
        :rtype: list
        """
        return [
            ("post_id", "=", False),
            (
                "published_date",
                "<",
                fields.Datetime.subtract(fields.Datetime.now(), days=days),
            ),
            ("state", "in", ["posted", "deleted"]),
        ]

    @api.autovacuum
    def _gc_aged_post_medias(self, limit=1000):
        """Release the medias downloaded for publications older than the policy.

        Only the medias this line downloaded are released: what it shares
        with a post belongs to the post, which is editorial content and is
        never aged out. The attachments are not deleted here — dropping them
        from the publication leaves them with no holder, and
        ``_gc_lost_media_attachments`` deletes them a day later, which is
        what marks the file for ``ir.attachment._gc_file_store``.

        ``media_refs`` is kept: it is what tells the next synchronization
        pass that this publication already had that media, and dropping it
        would only buy the same download again.

        :param limit: how many publications one pass reaches at most.
        """
        days = self._media_retention_days()
        if days <= 0:
            return
        lines = self.sudo().search(self._media_retention_domain(days), limit=limit)
        for line in lines:
            downloaded = (
                line.image_ids | line.video_ids
            ) - line._media_attachments_to_skip()
            if not downloaded:
                continue
            line.write(
                {
                    "image_ids": [
                        Command.unlink(media.id)
                        for media in downloaded & line.image_ids
                    ],
                    "video_ids": [
                        Command.unlink(media.id)
                        for media in downloaded & line.video_ids
                    ],
                }
            )
            _logger.info(
                "Released %(count)s medias of the publication %(line)s",
                {"count": len(downloaded), "line": line.id},
            )
