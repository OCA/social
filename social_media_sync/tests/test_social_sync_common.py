# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

PATCH_SYNC_MODELS = "odoo.addons.social_media_sync.models"
PATCH_SYNC_ACCOUNT = "{}.social_account.SocialAccount.{}".format(
    PATCH_SYNC_MODELS, "{}"
)
PATCH_SYNC_POST_ACCOUNT = "{}.social_post_account.SocialPostAccount.{}".format(
    PATCH_SYNC_MODELS, "{}"
)


def media_download_response(chunks=(), status_code=200, headers=None):
    """Return a streamed response of ``requests.get``, as a download reads it.

    The download opens the response as a context manager, reads its headers
    and then its body block by block.

    :param chunks: the blocks of the body.
    :param status_code: the HTTP status of the answer.
    :param headers: the headers of the answer.
    :rtype: unittest.mock.MagicMock
    """
    response = MagicMock()
    response.__enter__.return_value = response
    response.status_code = status_code
    response.headers = headers or {}
    response.iter_content.return_value = list(chunks)
    return response


class TestSocialMediaSyncCommon(TestSocialMediaBaseCommon):
    """The fixtures of the base module are enough for the synchronization.

    They are the same records — an account, a post, a publication; what changes
    is which module holds the code under test.
    """
