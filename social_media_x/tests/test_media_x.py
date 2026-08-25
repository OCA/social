# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_MEDIA,
)
from odoo.addons.social_media_x.tests.test_common_x import (
    TestSocialCommonX,
)


class TestSocialMediaX(TestSocialCommonX):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_action_open_account(self):
        with patch(
            PATCH_MEDIA.format("action_open_account")
        ) as mock_action_open_account:
            res = self.media_x_id.action_open_account()
            self.assertEqual(res["context"]["default_media_id"], self.media_x_id.id)
            mock_action_open_account.assert_called_once()

        with patch(
            PATCH_MEDIA.format("action_open_account")
        ) as mock__action_open_account:
            self.SocialMedia.action_open_account()
            mock__action_open_account.assert_called_once()
