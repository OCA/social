# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools
import logging
from urllib.parse import quote

import psycopg2

from odoo import Command, _, fields, models
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY
from odoo.tools import plaintext2html

from ..social_linkedin_utils import (
    _URL_FEED_UPDATE_LINKEDIN,
    _URN_COMMENT_LINKEDIN,
    _URN_IMAGE_LINKEDIN,
)

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    """Publication, comments and statistics of a post on a LinkedIn account."""

    _inherit = "social.post.account"

    def _get_linkedin_image_urns(self, content):
        """Return the image URNs carried by the content of a post.

        :param content: The ``content`` of the post answered by the Posts API.
        :rtype: list
        """
        media_id = str(content.get("media", {}).get("id", ""))
        image_urns = [media_id] if media_id.startswith(_URN_IMAGE_LINKEDIN) else []
        image_urns += [
            str(image.get("id", ""))
            for image in content.get("multiImage", {}).get("images", [])
            if str(image.get("id", "")).startswith(_URN_IMAGE_LINKEDIN)
        ]
        return image_urns

    def _remove_assets_deleted(self, content):
        """Drop the images that are no longer on the LinkedIn post.

        The publication mirrors what is online, so an image deleted on
        LinkedIn has to leave the dashboard card too. Only the attachments
        named after a LinkedIn URN are considered, so anything attached by
        hand in Odoo is never touched.

        The relation is unlinked before deleting the attachment: the field
        is declared with ``ondelete="restrict"``, so the database refuses to
        delete a media that a publication still points at.

        :param content: The ``content`` of the post answered by the Posts API.
        :return: The removed attachments.
        """
        self.ensure_one()
        remote_urns = self._get_linkedin_image_urns(content)
        removed = self.image_ids.filtered(
            lambda image: (image.name or "").startswith(_URN_IMAGE_LINKEDIN)
            and image.name not in remote_urns
        )
        if removed:
            self.image_ids = [Command.unlink(image.id) for image in removed]
            removed.sudo().unlink()
        return removed

    def _get_assets_save(self, content, account=None):
        """Download the images of a post that are not stored yet.

        :param content: The ``content`` of the post answered by the Posts API.
        :param account: The account to ask LinkedIn with, needed when the post
            does not exist in Odoo yet.
        :return: The commands creating the missing attachments.
        :rtype: list
        """
        image_urns = self._get_linkedin_image_urns(content)
        medias_exist = self._get_medias_account(image_urns)
        image_urns = [urn for urn in image_urns if urn not in medias_exist]
        if not image_urns:
            return []
        account = account or self.account_id
        download_urls = account._get_linkedin_images_download_url(image_urns)
        commands = [
            self._map_medias_account(**{"name": urn, "url": download_urls[urn]})
            for urn in image_urns
            if download_urls.get(urn)
        ]
        return [command for command in commands if command]

    def _linkedin_published_values(self, post_entity):
        """Return the extra values to store once the post is online.

        Extension point. It runs after ``remote_ref`` has been written and
        inside :meth:`_publish_guard`, so an implementation must never let an
        error escape: rolling back here would drop the reference of a post
        that already exists on LinkedIn.
        """
        self.ensure_one()
        return {}

    def _action_post(self, post_id):
        res = super()._action_post(post_id)
        if any(account.media_type == "linkedin" for account in post_id.account_ids):
            post_accounts = post_id._filter_by_media_types(["linkedin"])
            images, videos = post_id._medias_for_publication()
            for post_account in post_accounts:
                with post_account._publish_guard():
                    post_account._check_publishable()
                    (
                        post_entity,
                        image_urns,
                    ) = post_account._publish_attempt(
                        post_account.account_id._linkedin_create_post,
                        message=post_account.message,
                        image_ids=images,
                        video_ids=videos,
                    )
                    if post_entity:
                        post_account.write(
                            {
                                "remote_ref": post_entity,
                                "post_account_url": (
                                    f"{_URL_FEED_UPDATE_LINKEDIN}{post_entity}"
                                ),
                                "has_video": bool(videos),
                                "state": "posted",
                                "published_date": fields.Datetime.now(),
                                "failed_description": False,
                            }
                        )
                        post_account._linkedin_enrich_published_post(
                            post_entity, image_urns, images
                        )
                    else:
                        post_account.write(
                            {
                                "state": "failed",
                                "failed_description": plaintext2html(
                                    _(
                                        "The account has no LinkedIn access "
                                        "token. Update the account to "
                                        "authorize it again."
                                    )
                                ),
                            }
                        )
                        post_account.account_id._flag_credentials_expired(
                            _("the account has no access token")
                        )
        return res

    def _linkedin_enrich_published_post(
        self, post_entity, image_urns=None, images=None
    ):
        """Complete a publication that is already online on LinkedIn.

        Downloading the images is a best-effort step, and so are the extra
        values that extension modules add through
        :meth:`_linkedin_published_values`. The post exists on the social
        media, so a failure here must never revert its remote reference:
        errors are logged and reported on the post instead of being raised.

        LinkedIn does not always expose the images of a post right after
        creating it, so when the download brings nothing back the local
        attachments are copied instead: the dashboard card is never empty and
        the media does not have to wait for the next synchronization.

        :param post_entity: URN of the post created on LinkedIn.
        :param image_urns: URNs of the images attached to the post, in the
            same order as the local attachments that produced them.
        :param images: The attachments that produced ``image_urns``. They are
            received instead of read again so that both lists pair up by
            construction and not because two reads happen to agree on the
            order. Defaults to the images of the post.
        """
        self.ensure_one()
        values = {}
        attach_images = []
        try:
            ugc_post = self.account_id._get_posts(
                **{
                    "params_fields": ["ids"],
                    "params_values": {"ids": [post_entity]},
                }
            )
            if ugc_post and ugc_post[0].get("content", False):
                attach_images = self._get_assets_save(ugc_post[0].get("content", {}))
        except psycopg2.OperationalError as error:
            if error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                raise
            _logger.exception(
                "Error retrieving the medias of the LinkedIn post %s", post_entity
            )
        except Exception:  # noqa: BLE001 - the post is already published
            _logger.exception(
                "Error retrieving the medias of the LinkedIn post %s", post_entity
            )
        if not attach_images and image_urns:
            if images is None:
                images = self._sorted_medias(self.post_id.image_ids)
            attach_images = self._copy_medias_account(images, image_urns)
        if attach_images:
            values["image_ids"] = attach_images
        values.update(self._linkedin_published_values(post_entity))
        if values:
            self.write(values)

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
            headers=self.account_id.media_id._get_linkedin_headers(
                self.account_id.sudo().access_token, content_type="application/json"
            ),
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

    def action_like_post(self, author_urn=None):
        res = super().action_like_post(author_urn)
        if self.media_id.media_type == "linkedin":
            like_ok = False
            post_deleted = False
            response = self._react_linkedin(self.remote_ref, author_urn)
            message_like = ""
            if response.status_code == 201:
                like_ok = True
            elif response.status_code == 409:
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
            return {
                "success": like_ok,
                "message": message_like,
                "post_deleted": post_deleted,
            }
        return res

    def action_like_comment(self, comment_ref=None, author_urn=None):
        res = super().action_like_comment(comment_ref, author_urn)
        if self.media_id.media_type == "linkedin":
            like_ok = False
            post_deleted = False
            message_like = ""
            if not comment_ref:
                # The comment carries no URN, so there is nothing to react to.
                return {
                    "success": False,
                    "message": _("The comment cannot be recommended on LinkedIn."),
                    "post_deleted": False,
                }
            response = self._react_linkedin(comment_ref, author_urn)
            if response.status_code == 201:
                like_ok = True
            elif response.status_code == 409:
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

    def _linkedin_comment_values(self, element):
        """Map one comment as LinkedIn answers it to what the client draws.

        The same element arrives whether the social action asked for was a
        post or a comment, so the mapping is shared: a reply is a comment
        whose ``object`` is another comment instead of the publication, and
        that is what tells the client from whom it hangs.

        ``$URN`` is the reference LinkedIn itself puts on the element, and it
        is preferred over the URN built by hand, which stays as the fallback
        for the element that does not carry it.

        :param element: one comment as LinkedIn answered it.
        :return: the comment, shaped as ``get_comments`` documents it.
        :rtype: dict
        """
        thread_urn = element.get("object") or ""
        return {
            "id": element.get("id"),
            "remote_ref": element.get("$URN") or self._linkedin_comment_urn(element),
            "parent_ref": (
                thread_urn if thread_urn.startswith(_URN_COMMENT_LINKEDIN) else False
            ),
            # The comments of a post arrive with no summary of their replies,
            # so how many each one has is only known once they are asked for.
            "reply_count": None,
            "text": element.get("message", {}).get("text"),
            "actor": element.get("lastModified", {}).get("actor", {}),
            "published_time": self._format_published_time(
                element.get("lastModified", {}).get("time", 0)
            ),
            "images_url": [val.get("url", {}) for val in element.get("content", {})],
        }

    def get_comments(self):
        data = super().get_comments()
        comments = []
        if self.account_id.media_type == "linkedin" and self.remote_ref:
            response = self.account_id._request_linkedin(
                method="GET",
                endpoint=f"/socialActions/{quote(self.remote_ref)}/comments",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.sudo().access_token
                ),
                token=True,
                return_json=False,
                linkedin_v2=True,
            )
            if response.status_code == 200:
                response_comments = response.json().get("elements", [])
                comments = [
                    self._linkedin_comment_values(comment)
                    for comment in response_comments
                ]
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
            "data": list(itertools.chain(data.get("data", []), comments)),
        }

    def get_comment_replies(self, comment_ref):
        if self.account_id.media_type != "linkedin":
            return super().get_comment_replies(comment_ref)
        response = self.account_id._request_linkedin(
            method="GET",
            endpoint=f"/socialActions/{quote(comment_ref)}/comments",
            headers=self.account_id.media_id._get_linkedin_headers(
                self.account_id.sudo().access_token
            ),
            token=True,
            return_json=False,
            linkedin_v2=True,
        )
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
            "data": [
                self._linkedin_comment_values(element)
                for element in payload.get("elements", [])
            ],
            # LinkedIn answers how many replies the comment has in the same
            # payload as the replies themselves, which is the only moment it
            # says it at all.
            "count": payload.get("paging", {}).get("total", 0),
        }

    def _create_linkedin_comment(self, post_data):
        if self.account_id.media_type == "linkedin":
            # A reply is published on the social action of the comment it
            # answers, exactly as a comment is published on the one of the
            # post. Without a target it is the post, which is where a
            # first-level comment belongs.
            target = post_data.get("social_parent_ref") or self.remote_ref
            json_data = {
                "actor": self.account_id.remote_ref,
                "message": {"text": post_data.get("body", "")},
                "object": target,
            }
            response = self.account_id._request_linkedin(
                method="POST",
                endpoint=f"/socialActions/{quote(target)}/comments",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.sudo().access_token
                ),
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
        }

    def create_comment(self, post_data, context=None):
        if self.account_id.media_type == "linkedin":
            return self._create_linkedin_comment(post_data)
        else:
            return super().create_comment(post_data, context)

    def delete_linkedin_comment(self, comment_id, actor_urn):
        if self.account_id.media_type == "linkedin":
            response = self.account_id._request_linkedin(
                method="DELETE",
                endpoint=f"/socialActions/{quote(self.remote_ref)}/comments/{quote(comment_id)}",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.sudo().access_token
                ),
                params_fields=["actor"],
                params_values={"actor": actor_urn},
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

    def _check_remote_post_exists(self):
        """Read the post on LinkedIn to know whether it is still online.

        Only a ``404`` is treated as a deletion. Any other answer means
        LinkedIn could not be asked, not that the publication is gone: a
        ``403`` is a lost page role, a ``429`` a throttled application, and
        acting on them would mark a live publication as deleted.
        """
        if self.account_id.media_type != "linkedin" or not self.remote_ref:
            return super()._check_remote_post_exists()
        try:
            response = self.account_id._request_linkedin(
                endpoint=f"/posts/{quote(self.remote_ref)}",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.sudo().access_token
                ),
                return_json=False,
            )
        except Exception:  # noqa: BLE001 - unreachable is not deleted
            _logger.exception(
                "Error checking the LinkedIn post %s, it is left untouched",
                self.remote_ref,
            )
            return True
        if response.status_code == 404:
            self._register_remote_post_gone()
            return False
        if response.status_code != 200:
            _logger.warning(
                "LinkedIn answered %(code)s while checking the post %(post)s, "
                "it is left untouched: %(error)s",
                {
                    "code": response.status_code,
                    "post": self.remote_ref,
                    "error": self.account_id._linkedin_error_message(response),
                },
            )
        return True

    def _delete_post_account(self):
        if self.media_id.media_type == "linkedin" and self.remote_ref:
            self.account_id.with_context(not_notify=True).validate_access_token()
            delete_post = self.account_id._request_linkedin(
                method="DELETE",
                endpoint=f"/posts/{quote(self.remote_ref)}",
                headers=self.media_id._get_linkedin_headers(
                    self.account_id.sudo().access_token
                ),
                return_json=False,
            )
            if delete_post.status_code != 204:
                error_message = self.account_id._linkedin_error_message(
                    delete_post
                ) or _("The post could not be deleted, please try again later.")
                raise UserError(
                    _("Error deleting LinkedIn post: %(error)s", error=error_message)
                )
        return super()._delete_post_account()
