# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

PATCH_SYNC_MODELS = "odoo.addons.social_media_sync.models"
PATCH_SYNC_ACCOUNT = "{}.social_account.SocialAccount.{}".format(
    PATCH_SYNC_MODELS, "{}"
)


class TestSocialMediaSyncCommon(TestSocialMediaBaseCommon):
    """The fixtures of the base module are enough for the synchronization.

    They are the same records — an account, a post, a publication; what changes
    is which module holds the code under test.
    """
