# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from tweepy.errors import Forbidden, TooManyRequests, Unauthorized

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.social_media_base.exceptions import SocialCredentialsError

from ..social_x_utils import _URL_X

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    """Publishing, deletion and verification of a post on an X account."""

    _inherit = "social.post.account"

    def _action_post(self, post_id):
        res = super()._action_post(post_id)
        if any(account.media_type == "x" for account in post_id.account_ids):
            post_accounts = post_id._filter_by_media_types(["x"])
            images, videos = post_id._medias_for_publication()
            for post_account in post_accounts:
                with post_account._publish_guard():
                    post_account._check_publishable()
                    (
                        post_account_id,
                        media_refs,
                    ) = post_account._publish_attempt(
                        post_account.account_id.create_tweet,
                        message=post_account.message,
                        image_ids=images,
                        video_ids=videos,
                        post_id=post_id,
                        post_account_id=post_account,
                    )
                    if post_account_id:
                        post_account._register_publish_success(
                            post_account_id,
                            f"{_URL_X}{post_account.account_id.username}"
                            f"/status/{post_account_id}",
                            media_refs,
                            bool(videos),
                        )
                    else:
                        post_account._register_publish_refused(
                            _(
                                "X did not accept the post. The account may "
                                "have reached the limit of requests of its "
                                "plan: check the account and try again later."
                            )
                        )
        return res

    def _delete_post_account(self):
        """Delete the tweet of this publication before its line goes.

        The caller unlinks the line right after this, and the line is the only
        place holding ``remote_ref``, so a deletion X did not confirm has to
        stop here: otherwise the tweet stays published with nothing in Odoo
        pointing at it. The quota is such a deletion, and it is raised with
        the same reason the publication gives, because it is a time to wait
        and not a post X refused.

        A token X refuses flags the account the same way :meth:`create_tweet`
        does, because deleting is one of the few calls that still runs it:
        OAuth1 tokens do not expire on their own dates, so a call refused for
        credentials is the only way X's connector learns one was revoked.
        """
        if self.media_id.media_type == "x":
            message_error = ""
            quota_error = _(
                "The post could not be deleted on X. The account may have "
                "reached the limit of requests of its plan: check the account "
                "and try again later."
            )
            try:
                if self.remote_ref:
                    # Asking about the quota is not a mute question: with the
                    # window still open it tells the user when to retry. On a
                    # line that never reached X there is nothing to delete, so
                    # there is nothing to warn about either.
                    if not self.account_id._valid_time_request(endpoint="delete_post"):
                        message_error = quota_error
                    else:
                        client_api = self.account_id.get_client_api(
                            bearer_token=self.account_id.sudo().x_access_token_oauth2
                        )
                        response = client_api.delete_tweet(self.remote_ref)
                        if response.errors:
                            # tweepy answers the errors as dicts, so what X
                            # said is under its message key; the dict itself
                            # is the fallback for a shape without one.
                            message_error = ", ".join(
                                str(
                                    error.get("detail") or error.get("message") or error
                                )
                                for error in response.errors
                            )
            except TooManyRequests as exManyRequest:
                self.account_id._get_message_many_requests(
                    exManyRequest, endpoint="delete_post"
                )
                message_error = quota_error
            except (Unauthorized, Forbidden) as error:
                self.account_id._flag_credentials_expired(str(error))
                raise SocialCredentialsError(
                    _("DELETING POST ON X: %(error)s", error=error)
                ) from error
            except Exception as e:  # noqa: BLE001 - tweepy may fail in any way
                message_error = _("ERROR DELETE POST X: %(error)s", error=e)
                _logger.exception("Error deleting tweet %s", self.remote_ref)
            if message_error:
                raise UserError(message_error)
        return super()._delete_post_account()

    def _check_remote_post_exists(self):
        """Read the post on X to know whether it is still online.

        Only the ``Not Found`` answer of X is treated as a deletion. A
        throttled application or any other failure means the post could not
        be read, not that it is gone, so the record is left untouched — a
        token X refuses still flags the account, but the line itself is left
        alone and the answer stays ``True``, matching the fail-open contract
        of :meth:`~odoo.addons.social_media_base.models.social_post_account.
        SocialPostAccount._check_remote_post_exists`.
        """
        if self.account_id.media_type != "x" or not self.remote_ref:
            return super()._check_remote_post_exists()
        try:
            if not self.account_id._valid_time_request(endpoint="get_post"):
                return True
            client_api = self.account_id.get_client_api(
                bearer_token=self.account_id.sudo().x_access_token_oauth2
            )
            response = client_api.get_tweet(self.remote_ref, tweet_fields=["id"])
        except TooManyRequests as exManyRequest:
            self.account_id._get_message_many_requests(
                exManyRequest, endpoint="get_post"
            )
            return True
        except (Unauthorized, Forbidden) as error:
            self.account_id._flag_credentials_expired(str(error))
            return True
        except Exception:  # noqa: BLE001 - unreachable is not deleted
            _logger.exception(
                "Error checking the X post %s, it is left untouched",
                self.remote_ref,
            )
            return True
        if self._is_x_not_found(response):
            self._register_remote_post_gone()
            return False
        if response.errors:
            _logger.warning(
                "X answered with errors while checking the post %(post)s, it "
                "is left untouched: %(errors)s",
                {"post": self.remote_ref, "errors": response.errors},
            )
        return True

    def _is_x_not_found(self, response):
        """Whether X answered that the post does not exist any more.

        X reports a deleted post as a partial error carrying the
        ``resource-not-found`` type instead of raising, so the answer has to
        be read rather than the exception caught.

        :param response: the ``tweepy.Response`` of a tweet read.
        :rtype: bool
        """
        return any(
            "resource-not-found" in str(error.get("type", ""))
            or "Not Found" in str(error.get("title", ""))
            for error in response.errors or []
            if isinstance(error, dict)
        )
