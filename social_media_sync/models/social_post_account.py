# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime

import pytz

from odoo import _, models
from odoo.tools.misc import _format_time_ago

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    """What the publication reads back from its social media.

    Asking whether a publication is still there costs one call per
    publication, and reading a thread costs one per thread: both grow with
    what the account has published, which is why neither is in
    ``social_media_base``.
    """

    _inherit = "social.post.account"

    def action_open_post_account_url(self):
        """Ask the social media before opening the address.

        The address alone is not proof that the publication is still online:
        it survives a deletion made on the social media until a pass notices.
        Base opens it without asking because asking costs a call per
        publication; here the call is what this module is for.
        """
        result = super().action_open_post_account_url()
        if not result:
            return result
        if not self.check_post_exists():
            return self._notify_remote_post_gone()
        return result

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

    def _register_remote_post_gone(self):
        """Record that the publication no longer exists on the social media.

        ``remote_ref`` is kept on purpose: it is the only handle left on the
        publication, and detection is not infallible, so a line wrongly marked
        can be recognised and restored by the next full refresh.
        """
        self.write({"state": "deleted", "post_account_url": False})

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

    def action_like_post(self, author_urn=None):
        """Like the publication on the social media.

        :param author_urn: actor urn performing the like.
        :return: ``success`` and ``message`` of the action, plus
            ``post_deleted`` when the attempt is what revealed the publication
            is gone, so the client refreshes what it draws.
        :rtype: dict
        """
        return {"success": True, "message": "", "post_deleted": False}

    def action_like_comment(self, comment_ref=None, author_urn=None):
        """Like a comment of the publication on the social media.

        :param comment_ref: reference of the comment on the social media, as
            ``get_comments`` answered it in ``remote_ref``.
        :param author_urn: actor urn performing the like.
        :return: ``success`` and ``message`` of the action, plus
            ``post_deleted`` as :meth:`action_like_post` documents it.
        :rtype: dict
        """
        return {"success": True, "message": "", "post_deleted": False}

    def get_comments(self):
        """Retrieve the comments of the publication.

        Every element of ``data`` is a comment as the client draws it::

            {
                "id": "7491701601242423296",
                "remote_ref": "urn:li:comment:(urn:li:activity:749…,749…)",
                "parent_ref": False,
                "reply_count": None,
                "text": "Comment",
                "actor": "urn:li:person:_prFA0zDNN",
                "published_time": "2 weeks ago",
                "images_url": [],
            }

        ``remote_ref`` is what names the comment on the social media, and what
        travels back as the target of a reply. ``parent_ref`` is the
        ``remote_ref`` of the comment this one hangs from, ``False`` when it
        hangs from the publication itself. ``reply_count`` is how many replies
        it has, and ``None`` when the social media does not say without being
        asked for it — LinkedIn answers the comments of a post without any
        summary of their replies, so the count only arrives with
        ``get_comment_replies``.

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

    def create_comment(self, post_data, context=None):
        """Create a comment on the social media.

        A reply is created the same way a first-level comment is: the client
        puts the ``remote_ref`` of the comment being answered in
        ``post_data["social_parent_ref"]``, and the key is simply absent when
        the comment hangs from the publication.

        :param post_data: message and other data of the comment.
        :param context: optional context used to render the comment.
        :return: ``success`` and ``data`` of the action, plus ``post_deleted``
            when the attempt is what revealed the publication is gone.
        :rtype: dict
        """

    def _format_published_time(self, milliseconds):
        """Return how long ago a moment is, ready to be shown to the user.

        The comments and the publications the social media answer carry their
        moment as an epoch, and the client draws it as "3 days ago" next to
        each one. ``_format_time_ago`` wraps ``babel.dates.format_timedelta``,
        so the text comes out in the language of the user and with the
        direction a reader expects: "3 days ago" rather than "3 days". The
        core reads it the same way for the same purpose in
        ``addons/website/models/website_visitor.py``.

        The moment is built in UTC because that is what the social media APIs
        answer, and the delta is taken against a UTC now so that the two ends
        of the subtraction are comparable.

        :param milliseconds: the moment, in milliseconds since the epoch.
        :rtype: str
        """
        value = datetime.fromtimestamp(milliseconds / 1000, tz=pytz.utc)
        return _format_time_ago(self.env, datetime.now(pytz.utc) - value)
