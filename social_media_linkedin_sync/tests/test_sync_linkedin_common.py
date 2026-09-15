# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import tagged

from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    TestSocialCommonLinkedin,
)

PATCH_SYNC_LINKEDIN_MODELS = "odoo.addons.social_media_linkedin_sync.models"
PATCH_SYNC_ACCOUNT_LINKEDIN = "{}.social_account.SocialAccount.{}".format(
    PATCH_SYNC_LINKEDIN_MODELS, "{}"
)
PATCH_SYNC_POST_ACCOUNT_LINKEDIN = "{}.social_post_account.SocialPostAccount.{}".format(
    PATCH_SYNC_LINKEDIN_MODELS, "{}"
)


@tagged("post_install", "-at_install")
class TestSocialSyncCommonLinkedin(TestSocialCommonLinkedin):
    """The fixtures of the connector are enough to synchronize LinkedIn.

    They are the same records — the wizard, the media, the account, the post
    and its publication; what changes is which module holds the code under
    test. Subclassed instead of moved because three test files of
    ``social_media_advertising_linkedin`` import the connector's own, and that
    module knows nothing about synchronizing.
    """
