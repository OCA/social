# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from urllib.parse import quote

import psycopg2

from odoo import _, models
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY
from odoo.tools import split_every

from ..social_linkedin_utils import (
    _BATCH_GET_MAX_IDS_LINKEDIN,
    _ENDPOINT_POST_LINKEDIN,
    _SCOPE_READ_POSTS_LINKEDIN,
    _URL_FEED_UPDATE_LINKEDIN,
    _URN_IMAGE_LINKEDIN,
)

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    """Publish, delete and verify a post on a LinkedIn account.

    A fixed number of calls per publication, whatever the history of the
    page: publishing it, deleting it, and the single call that answers
    whether the publication the user is opening is still online. Walking
    what the page has published — its comments, its reactions, the whole
    feed — costs one call per publication or per thread and lives in
    ``social_media_linkedin_sync``.
    """

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
                        media_refs,
                    ) = post_account._publish_attempt(
                        post_account.account_id._linkedin_create_post,
                        message=post_account.message,
                        image_ids=images,
                        video_ids=videos,
                    )
                    if post_entity:
                        post_account._register_publish_success(
                            post_entity,
                            f"{_URL_FEED_UPDATE_LINKEDIN}{post_entity}",
                            media_refs,
                            bool(videos),
                        )
                        post_account._linkedin_enrich_published_post(post_entity)
                    else:
                        post_account._register_publish_refused(
                            _(
                                "The account has no LinkedIn access token. "
                                "Update the account to authorize it again."
                            )
                        )
                        post_account.account_id._flag_credentials_expired(
                            _("the account has no access token")
                        )
        return res

    def _linkedin_enrich_published_post(self, post_entity):
        """Complete a publication that is already online on LinkedIn.

        The extra values that extension modules add through
        :meth:`_linkedin_published_values` are a best-effort step. The post
        exists on the social media, so a failure here must never revert its
        remote reference: errors are logged and reported on the post instead
        of being raised.

        The medias are not asked for: the publication shares the attachments
        of its post and already knows, from ``media_refs``, what each of them
        became on LinkedIn.

        :param post_entity: URN of the post created on LinkedIn.
        """
        self.ensure_one()
        values = {}
        try:
            values = self._linkedin_published_values(post_entity)
        except psycopg2.OperationalError as error:
            if error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                raise
            _logger.exception(
                "Error completing the published LinkedIn post %s", post_entity
            )
        except Exception:  # noqa: BLE001 - the post is already published
            _logger.exception(
                "Error completing the published LinkedIn post %s", post_entity
            )
        if values:
            self.write(values)

    def _linkedin_headers(self, **kwargs):
        """Return the headers of a call about this publication.

        Every call about a publication travels on the token of the account it
        belongs to, so the token is filled in here instead of at each call
        site. Anything else the call needs goes through as it is.

        :rtype: dict
        """
        return self.account_id.media_id._get_linkedin_headers(
            self.account_id.sudo().access_token, **kwargs
        )

    def _check_remote_post_exists(self):
        """Read the post on LinkedIn to know whether it is still online.

        Only a ``404`` is treated as a deletion. Any other answer means
        LinkedIn could not be asked, not that the publication is gone: a
        ``403`` is a lost page role, a ``429`` a throttled application, and
        acting on them would mark a live publication as deleted.
        """
        if self.account_id.media_type != "linkedin" or not self.remote_ref:
            return super()._check_remote_post_exists()
        self.account_id._check_linkedin_scopes(_SCOPE_READ_POSTS_LINKEDIN)
        try:
            response = self.account_id._request_linkedin(
                endpoint=_ENDPOINT_POST_LINKEDIN % quote(self.remote_ref),
                headers=self._linkedin_headers(),
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

    def _check_remote_posts_exist(self):
        """Confirm a batch of suspects in one call per hundred.

        The Posts API answers a ``BATCH_GET`` by ``ids``, so the price of
        confirming a deletion is one call per ``_BATCH_GET_MAX_IDS_LINKEDIN``
        suspects and not one per suspect, which is what makes it affordable
        for the pass that sweeps the whole feed.

        The lines are asked about one account at a time: each account has its
        own token and its own page role, and a URN is asked about from the
        account that published it.
        """
        linkedin = self.filtered(
            lambda line: line.account_id.media_type == "linkedin" and line.remote_ref
        )
        others = self - linkedin
        gone = super(SocialPostAccount, others)._check_remote_posts_exist()
        confirmed = set()
        for account, lines in linkedin.grouped("account_id").items():
            account._check_linkedin_scopes(_SCOPE_READ_POSTS_LINKEDIN)
            for batch in split_every(
                _BATCH_GET_MAX_IDS_LINKEDIN, lines.mapped("remote_ref"), list
            ):
                confirmed |= account._get_posts_gone(batch)
        return gone | linkedin.filtered(lambda line: line.remote_ref in confirmed)

    def _delete_post_account(self):
        if self.media_id.media_type == "linkedin" and self.remote_ref:
            self.account_id.with_context(not_notify=True).validate_access_token()
            delete_post = self.account_id._request_linkedin(
                method="DELETE",
                endpoint=_ENDPOINT_POST_LINKEDIN % quote(self.remote_ref),
                headers=self._linkedin_headers(),
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
