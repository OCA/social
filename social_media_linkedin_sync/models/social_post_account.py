# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from urllib.parse import quote

from odoo import Command, _, models

from odoo.addons.social_media_linkedin.social_linkedin_utils import (
    _SCOPE_READ_POSTS_LINKEDIN,
    datetime_from_epoch_milliseconds,
)

from ..social_linkedin_sync_utils import (
    _URN_COMMENT_LINKEDIN,
    _URN_PERSON_LINKEDIN,
    linkedin_reaction_id,
)

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    """Comments, reactions and remote verification of a LinkedIn publication.

    What a call costs is what puts these here and not in the connector: one
    call per publication only to ask whether it still exists, one call per
    comment thread, one more per thread of replies. The connector keeps
    publishing and deleting, which cost a fixed number of calls whatever the
    history of the page.
    """

    _inherit = "social.post.account"

    def _get_assets_save(self, content, account=None):
        """Download the images of a post that are not stored yet.

        One download per image the publication does not have, so what it
        costs grows with the history of the account, which is what puts it
        here and not in the connector. Publishing needs none of this: the
        image it puts online is the one the post already holds.

        :param content: The ``content`` of the post answered by the Posts API.
        :param account: The account to ask LinkedIn with, needed when the post
            does not exist in Odoo yet.
        :return: The attachments created and the URN of each one, keyed by its
            identifier. Both go into the same write, so that a downloaded
            media is never stored without the reference telling it apart from
            one attached in Odoo.
        :rtype: tuple
        """
        Attachment = self.env["ir.attachment"]
        image_urns = self._get_linkedin_image_urns(content)
        medias_exist = self._get_medias_account(image_urns)
        image_urns = [urn for urn in image_urns if urn not in medias_exist]
        if not image_urns:
            return Attachment, {}
        account = account or self.account_id
        download_urls = account._get_linkedin_images_download_url(image_urns)
        return self._store_remote_medias(
            {urn: download_urls.get(urn) for urn in image_urns}
        )

    def _remove_assets_deleted(self, content):
        """Drop the images that are no longer on the LinkedIn post.

        The publication mirrors what is online, so an image deleted on
        LinkedIn has to leave the dashboard card too. ``media_refs`` is what
        tells which images that is: an image with a reference there came from
        LinkedIn, and one without it was attached by hand in Odoo and is
        never touched.

        The attachment is unlinked from the publication, which is what
        releases it when the publication owned it: ``write`` lets go of the
        medias a record stops carrying and the vacuum deletes them. A
        publication shares the attachments of its post, and those belong to
        the post, so they are left alone.

        The reference leaves ``media_refs`` in that very write, which is what
        ``_check_media_refs`` asks for: the publication never answers for a
        media it no longer holds.

        :param content: The ``content`` of the post answered by the Posts API.
        :return: The removed attachments.
        """
        self.ensure_one()
        remote_urns = self._get_linkedin_image_urns(content)
        refs = self.media_refs or {}
        removed = self.image_ids.filtered(
            lambda image: refs.get(str(image.id))
            and refs[str(image.id)] not in remote_urns
        )
        if removed:
            dropped = {str(image.id) for image in removed}
            self.write(
                {
                    "image_ids": [Command.unlink(image.id) for image in removed],
                    "media_refs": {
                        key: value for key, value in refs.items() if key not in dropped
                    },
                }
            )
        return removed

    def _react_linkedin(self, root, author_urn):
        """Create a LIKE reaction on a LinkedIn entity.

        The Reactions API takes the entity in ``root``, so the same call
        reacts to a publication and to one of its comments: the first one is
        a share or ugcPost URN, the second a composite comment URN.

        https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/reactions-api

        :param root: URN of the entity the reaction is created on.
        :param author_urn: actor urn performing the reaction.
        :return: the answer of LinkedIn, whatever its status code.
        """
        return self.account_id._request_linkedin(
            method="POST",
            endpoint="/reactions",
            headers=self._linkedin_headers(content_type="application/json"),
            token=True,
            return_json=False,
            linkedin_v2=True,
            params_fields=["actor"],
            params_values={"actor": author_urn},
            json_data={
                "root": root,
                "reactionType": "LIKE",
            },
        )

    def _unreact_linkedin(self, root, author_urn):
        """Withdraw the reaction of an actor from a LinkedIn entity.

        The Reactions API addresses the reaction by the pair that created it,
        so the same call withdraws one from a publication and from one of its
        comments. A successful deletion answers ``204``.

        https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/reactions-api

        :param root: URN of the entity the reaction was created on.
        :param author_urn: actor urn whose reaction is withdrawn.
        :return: the answer of LinkedIn, whatever its status code.
        """
        return self.account_id._request_linkedin(
            method="DELETE",
            endpoint=f"/reactions/{linkedin_reaction_id(author_urn, root)}",
            headers=self._linkedin_headers(),
            token=True,
            return_json=False,
            linkedin_v2=True,
        )

    def action_like_post(self, author_urn=None):
        res = super().action_like_post(author_urn)
        if self.media_id.media_type == "linkedin":
            like_ok = False
            post_deleted = False
            liked = self.liked_by_account
            response = self._react_linkedin(self.remote_ref, author_urn)
            message_like = ""
            if response.status_code == 201:
                like_ok = True
                liked = True
            elif response.status_code == 409:
                # The reaction was already there, so what Odoo drew was
                # stale. Answering it as reacted is what puts the two back in
                # step, and the next press withdraws it.
                liked = True
                message_like = _("You have already reacted to this post.")
            elif response.status_code == 404:
                post_deleted = self._remote_post_gone_on_action()
                message_like = (
                    _("The post does not exist or has been deleted.")
                    if post_deleted
                    else self.account_id._linkedin_error_message(response)
                )
            else:
                message_like = self.account_id._linkedin_error_message(response)
            self._store_liked_by_account(liked)
            return {
                "success": like_ok,
                "message": message_like,
                "post_deleted": post_deleted,
                "liked": liked,
            }
        return res

    def action_unlike_post(self, author_urn=None):
        res = super().action_unlike_post(author_urn)
        if self.media_id.media_type == "linkedin":
            unlike_ok = False
            post_deleted = False
            liked = self.liked_by_account
            response = self._unreact_linkedin(self.remote_ref, author_urn)
            message_unlike = ""
            if response.status_code == 204:
                unlike_ok = True
                liked = False
            elif response.status_code == 404:
                # The pair actor/entity is missing both when the reaction was
                # already withdrawn and when the publication itself is gone,
                # so the two are told apart by asking about the publication.
                post_deleted = self._remote_post_gone_on_action()
                if post_deleted:
                    message_unlike = _("The post does not exist or has been deleted.")
                else:
                    liked = False
                    message_unlike = _("You had no reaction on this post.")
            else:
                message_unlike = self.account_id._linkedin_error_message(response)
            self._store_liked_by_account(liked)
            return {
                "success": unlike_ok,
                "message": message_unlike,
                "post_deleted": post_deleted,
                "liked": liked,
            }
        return res

    def _store_liked_by_account(self, liked):
        """Keep what LinkedIn holds on the publication, without writing twice.

        The reaction of the account is read back on every import, so this is
        only what keeps the card in step between two of them.

        :param liked: whether the account holds a reaction on the publication.
        """
        if liked != self.liked_by_account:
            self.liked_by_account = liked

    def action_like_comment(self, comment_ref=None, author_urn=None):
        res = super().action_like_comment(comment_ref, author_urn)
        if self.media_id.media_type == "linkedin":
            like_ok = False
            post_deleted = False
            # ``None`` until LinkedIn says: an error that names nothing must
            # not redraw the entry as a reaction that is not there.
            liked = None
            message_like = ""
            if not comment_ref:
                # The comment carries no URN, so there is nothing to react to.
                return {
                    "success": False,
                    "message": _("The comment cannot be recommended on LinkedIn."),
                    "post_deleted": False,
                    "liked": None,
                }
            response = self._react_linkedin(comment_ref, author_urn)
            if response.status_code == 201:
                like_ok = True
                liked = True
            elif response.status_code == 409:
                liked = True
                message_like = _("You have already reacted to this comment.")
            elif response.status_code == 404:
                # A comment answers ``404`` on its own, but it also does when
                # the publication holding it is gone, so the two are told
                # apart by asking about the publication.
                post_deleted = self._remote_post_gone_on_action()
                message_like = (
                    _("The post does not exist or has been deleted.")
                    if post_deleted
                    else _("The comment does not exist or has been deleted.")
                )
            else:
                message_like = self.account_id._linkedin_error_message(response)
            return {
                "success": like_ok,
                "message": message_like,
                "post_deleted": post_deleted,
                "liked": liked,
            }
        return res

    def action_unlike_comment(self, comment_ref=None, author_urn=None):
        res = super().action_unlike_comment(comment_ref, author_urn)
        if self.media_id.media_type == "linkedin":
            unlike_ok = False
            post_deleted = False
            liked = None
            message_unlike = ""
            if not comment_ref:
                return {
                    "success": False,
                    "message": _("The comment cannot be recommended on LinkedIn."),
                    "post_deleted": False,
                    "liked": None,
                }
            response = self._unreact_linkedin(comment_ref, author_urn)
            if response.status_code == 204:
                unlike_ok = True
                liked = False
            elif response.status_code == 404:
                # Told apart the same way the reaction is: the pair is
                # missing both when it was already withdrawn and when the
                # publication holding the comment is gone.
                post_deleted = self._remote_post_gone_on_action()
                if post_deleted:
                    message_unlike = _("The post does not exist or has been deleted.")
                else:
                    liked = False
                    message_unlike = _("You had no reaction on this comment.")
            else:
                message_unlike = self.account_id._linkedin_error_message(response)
            return {
                "success": unlike_ok,
                "message": message_unlike,
                "post_deleted": post_deleted,
                "liked": liked,
            }
        return res

    def _linkedin_comment_urn(self, comment):
        """Return the composite URN of a comment answered by LinkedIn.

        The Reactions API only takes the comment in that form,
        ``urn:li:comment:(urn:li:activity:6666,120381273128)``: the URN of the
        thread the comment is on and its identifier. The versioned Comments
        API answers it in ``commentUrn``, but the ``socialActions`` endpoint
        this connector reads does not always carry that field, so it is built
        from the thread the comment itself reports in ``object``.

        https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/comments-api

        :param comment: one comment as LinkedIn answered it.
        :return: the composite URN, empty when the thread is not known.
        :rtype: str
        """
        comment_urn = comment.get("commentUrn")
        if comment_urn:
            return comment_urn
        thread_urn = comment.get("object") or self.remote_ref
        comment_id = comment.get("id")
        if not thread_urn or not comment_id:
            return ""
        return f"{_URN_COMMENT_LINKEDIN}({thread_urn},{comment_id})"

    def _linkedin_comment_stamp(self, element):
        """Return who wrote a comment and when, as LinkedIn stamps it.

        A comment read from a social action carries ``lastModified``, and one
        LinkedIn has just created carries only ``created``. Both are the same
        ``{"actor": …, "time": …}`` pair, so whichever is present answers.

        :param element: one comment as LinkedIn answered it.
        :rtype: dict
        """
        return element.get("lastModified") or element.get("created") or {}

    def _linkedin_comment_time(self, element):
        """Return the moment LinkedIn stamps a comment with.

        LinkedIn answers it as an epoch in milliseconds, and the conversion
        belongs here: the generic side takes a moment from every connector and
        turns it into the same sentence for all of them.

        The epoch is read in UTC, which is what the API answers, and the
        moment comes back naive, the way a ``Datetime`` field holds it. An
        element LinkedIn stamped with nothing answers nothing, so the
        comment is drawn without a date instead of one written in 1970.

        :param element: one comment as LinkedIn answered it.
        :return: the moment it was written, or ``False`` when it is not
            stamped.
        :rtype: datetime.datetime or bool
        """
        milliseconds = self._linkedin_comment_stamp(element).get("time")
        if not milliseconds:
            return False
        return datetime_from_epoch_milliseconds(milliseconds)

    def _linkedin_comment_values(self, element):
        """Map one comment as LinkedIn answers it to what the client draws.

        The same element arrives whether the social action asked for was a
        post or a comment, so the mapping is shared: ``object`` is the
        publication the thread lives on for every comment, and
        ``parentComment`` —which only a reply carries— is what tells the
        client from whom it hangs.

        ``$URN`` is the reference LinkedIn itself puts on the element, and it
        is preferred over the URN built by hand, which stays as the fallback
        for the element that does not carry it.

        :param element: one comment as LinkedIn answered it.
        :return: the comment, shaped as ``get_comments`` documents it.
        :rtype: dict
        """
        return {
            "id": element.get("id"),
            "remote_ref": element.get("$URN") or self._linkedin_comment_urn(element),
            "parent_ref": element.get("parentComment") or False,
            # The comments of a post arrive with no summary of their replies,
            # so how many each one has is only known once they are asked for.
            "reply_count": None,
            "text": element.get("message", {}).get("text"),
            # ``lastModified`` is what a comment read from the thread carries,
            # and ``created`` —the same ``{actor, time}`` pair— is all a
            # comment LinkedIn has just created answers with.
            "actor": self._linkedin_comment_stamp(element).get("actor", {}),
            "published_time": self._format_published_time(
                self._linkedin_comment_time(element)
            ),
            "images_url": [val.get("url", {}) for val in element.get("content", {})],
            # Filled in for the whole thread at once by
            # :meth:`_mark_liked_comments`, one call instead of one per
            # comment.
            "liked": False,
        }

    def _mark_liked_comments(self, comments):
        """Say which of the comments the account already reacted to.

        One batch for the whole thread: the alternative is asking LinkedIn
        once per comment, and a thread has as many comments as it has.

        :param comments: the comments as the client draws them.
        :return: the same comments, with ``liked`` filled in.
        :rtype: list
        """
        reacted = self.account_id._get_reactions(
            [comment.get("remote_ref") for comment in comments]
        )
        if reacted is None:
            # LinkedIn did not answer, so nothing is claimed: the entry stays
            # drawn as a reaction that can still be made.
            return comments
        for comment in comments:
            comment["liked"] = comment.get("remote_ref") in reacted
        return comments

    def _resolve_comment_actors(self, comments):
        """Write the name and the picture of whoever signed each comment.

        The brother of :meth:`_mark_liked_comments`, and for the same
        reason: the URNs of the whole batch are collected first and
        ``_get_linkedin_actors`` is called **once**, because the alternative
        is asking LinkedIn once per comment and a thread has as many comments
        as it has.

        What arrives in ``actor`` is the raw URN ``_linkedin_comment_values``
        copied from LinkedIn, and what leaves is always a readable name: the
        contract ``get_comments`` documents, and the one
        ``social_media_x_sync`` already answers.

        :param comments: the comments as the client draws them, their
            ``actor`` still holding the URN LinkedIn answered.
        :return: the same comments, with ``actor`` and ``author_image``
            written.
        :rtype: list
        """
        actors = self.account_id._get_linkedin_actors(
            [comment.get("actor") for comment in comments]
        )
        for comment in comments:
            name, image = self._linkedin_actor_label(comment.get("actor"), actors)
            comment["actor"] = name
            comment["author_image"] = image
        return comments

    def _linkedin_actor_label(self, urn, actors):
        """Return the name and the picture to draw for the actor of a comment.

        Three cases, tried in this order: the account itself, whose name and
        avatar are already in Odoo; an organization ``_get_linkedin_actors``
        resolved; and anything else, a neutral label. Nothing here falls back
        to whoever wrote the publication --a false name is worse than no
        name, and a comment signed by the page that did not write it is what
        this method exists to stop.

        The two neutral labels are told apart by the prefix of the URN.
        LinkedIn does not let a person be read at all, so that one is
        certain; anything else is a page whose name could not be read this
        time, and knowing it is a company is worth the second string.

        :param urn: what LinkedIn named the actor of the comment with,
            usually a URN and, on the comment that carries no stamp, a dict.
        :param actors: what ``_get_linkedin_actors`` resolved.
        :return: the ``(name, image)`` pair, the image being a URL or
            ``False``.
        :rtype: tuple
        """
        account = self.account_id
        if urn and urn == account.remote_ref:
            return account.name, f"/web/image/social.account/{account.id}/image_128"
        actor = actors.get(urn) if isinstance(urn, str) else None
        if actor:
            return actor["name"], actor.get("image", False)
        if isinstance(urn, str) and urn.startswith(_URN_PERSON_LINKEDIN):
            return _("LinkedIn member"), False
        return _("LinkedIn page"), False

    def _read_linkedin_comments(self, target):
        """Ask LinkedIn for the comments hanging from an entity.

        One endpoint answers both threads: the comments of a publication and
        the replies of a comment. What tells them apart is the URN it is
        asked about, so the two callers differ in that and in nothing else.

        :param target: the URN of the publication or of the comment.
        :return: the answer, left unchecked for the caller to word its own
            error.
        """
        return self.account_id._request_linkedin(
            method="GET",
            endpoint=f"/socialActions/{quote(target)}/comments",
            headers=self._linkedin_headers(),
            token=True,
            return_json=False,
            linkedin_v2=True,
        )

    def _shape_linkedin_comments(self, elements):
        """Turn the comments LinkedIn answered into what the dialog draws.

        :param elements: the ``elements`` of the answer.
        :rtype: list
        """
        return self._resolve_comment_actors(
            self._mark_liked_comments(
                [self._linkedin_comment_values(element) for element in elements]
            )
        )

    def get_comments(self):
        data = super().get_comments()
        if self.account_id.media_type != "linkedin":
            # Answered untouched, ``success`` included: what another social
            # media has to say about its own publications is not this
            # connector's to overwrite.
            return data
        self.account_id._check_linkedin_scopes(_SCOPE_READ_POSTS_LINKEDIN)
        comments = []
        if self.remote_ref:
            response = self._read_linkedin_comments(self.remote_ref)
            if response.status_code == 200:
                comments = self._shape_linkedin_comments(
                    response.json().get("elements", [])
                )
            else:
                return_message = _(
                    "The comments could not be read from LinkedIn: %(error)s",
                    error=self.account_id._linkedin_error_message(response),
                )
                _logger.error(
                    "Error getting the comments of LinkedIn post %s: %s",
                    self.remote_ref,
                    response.status_code,
                )
                return {
                    "success": False,
                    "message": return_message,
                }
        return {
            "success": True,
            "data": data.get("data", []) + comments,
        }

    def get_comment_replies(self, comment_ref):
        if self.account_id.media_type == "linkedin":
            self.account_id._check_linkedin_scopes(_SCOPE_READ_POSTS_LINKEDIN)
            response = self._read_linkedin_comments(comment_ref)
            if response.status_code != 200:
                return_message = _(
                    "The replies could not be read from LinkedIn: %(error)s",
                    error=self.account_id._linkedin_error_message(response),
                )
                _logger.error(
                    "Error getting the replies of LinkedIn comment %s: %s",
                    comment_ref,
                    response.status_code,
                )
                return {
                    "success": False,
                    "message": return_message,
                    "data": [],
                    "count": 0,
                }
            payload = response.json()
            return {
                "success": True,
                "data": self._shape_linkedin_comments(payload.get("elements", [])),
                # LinkedIn answers how many replies the comment has in the same
                # payload as the replies themselves, which is the only moment it
                # says it at all.
                "count": payload.get("paging", {}).get("total", 0),
            }
        return super().get_comment_replies(comment_ref)

    def _create_linkedin_comment(self, post_data):
        if self.account_id.media_type == "linkedin":
            # A reply is addressed to the social action of the comment it
            # answers, but what nests it is ``parentComment``: ``object`` is
            # the publication the thread lives on, for a reply as much as for
            # a first-level comment. Without a parent the address is the
            # post, which is where a first-level comment belongs.
            parent_ref = post_data.get("social_parent_ref")
            target = parent_ref or self.remote_ref
            json_data = {
                "actor": self.account_id.remote_ref,
                "message": {"text": post_data.get("body", "")},
                "object": self.remote_ref,
            }
            if parent_ref:
                json_data["parentComment"] = parent_ref
            response = self.account_id._request_linkedin(
                method="POST",
                endpoint=f"/socialActions/{quote(target)}/comments",
                headers=self._linkedin_headers(),
                json_data=json_data,
                token=True,
                return_json=False,
                linkedin_v2=True,
            )
            if response.status_code != 201:
                post_deleted = (
                    response.status_code == 404 and self._remote_post_gone_on_action()
                )
                return_message = (
                    _("The post does not exist or has been deleted.")
                    if post_deleted
                    else _(
                        "The comment could not be published on LinkedIn: %(error)s",
                        error=self.account_id._linkedin_error_message(response),
                    )
                )
                _logger.error(
                    "Error replying to LinkedIn post %s: %s",
                    target,
                    response.status_code,
                )
                return {
                    "success": False,
                    "message": return_message,
                    "post_deleted": post_deleted,
                }
            return {
                "success": True,
                "post_deleted": False,
                **self._linkedin_created_comment(response),
            }
        return {
            "success": True,
            "post_deleted": False,
        }

    def _linkedin_created_comment(self, response):
        """Shape the comment LinkedIn answers in the body of the creation.

        LinkedIn returns the comment it has just created in the ``201``, so
        the client can draw it without reading the thread again. Anything the
        body does not allow to shape answers nothing: the caller leaves the
        key out, and the client rereads the thread instead.

        :param response: the answer of LinkedIn to the creation.
        :return: ``{"comment": …}``, or empty when it cannot be shaped.
        :rtype: dict
        """
        try:
            element = response.json()
        except ValueError:
            _logger.warning(
                "LinkedIn created the comment on %s but answered no readable "
                "body, so the thread is read again to show it",
                self.remote_ref,
            )
            return {}
        if not isinstance(element, dict) or not element.get("id"):
            return {}
        comment = self._linkedin_comment_values(element)
        if not comment.get("remote_ref"):
            return {}
        # The comment was just written by this account, so its actor resolves
        # out of Odoo and the shortcut costs no call to LinkedIn.
        return {"comment": self._resolve_comment_actors([comment])[0]}

    def create_comment(self, post_data, context=None):
        if self.account_id.media_type == "linkedin":
            return self._create_linkedin_comment(post_data)
        else:
            return super().create_comment(post_data, context)

    def delete_comment(self, comment_ref):
        """Delete one comment of the thread of this publication.

        LinkedIn honours the deletion for the author of the comment and for
        the owner of the publication, and the owner is what this account is:
        moderating a comment of somebody else on its own post is the ordinary
        case. Which of the two the call acts as is read from the account, not
        from the caller, or an RPC could choose whom the deletion is
        attributed to.

        :param comment_ref: id of the comment to delete, inside this thread.
        :rtype: dict
        """
        if self.account_id.media_type != "linkedin":
            return super().delete_comment(comment_ref)
        response = self.account_id._request_linkedin(
            method="DELETE",
            endpoint=(
                f"/socialActions/{quote(self.remote_ref)}"
                f"/comments/{quote(comment_ref)}"
            ),
            headers=self._linkedin_headers(),
            params_fields=["actor"],
            params_values={"actor": self.account_id.remote_ref},
            token=True,
            return_json=False,
            linkedin_v2=True,
        )
        if response.status_code != 204:
            return {
                "success": False,
                "message": _(
                    "An error occurred while deleting the comment or it "
                    "no longer exists, please try again later."
                ),
            }
        return {
            "success": True,
        }
