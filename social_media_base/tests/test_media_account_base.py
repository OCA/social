# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.fields import Command

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)


class TestSocialMediaBase(TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_action_like_comment(self):
        result = self.SocialPostAccount.action_like_comment()
        self.assertEqual(result, {"success": True, "message": ""})

    def test_filter_by_media_types(self):
        result = self.SocialPost.filter_by_media_types([])
        self.assertEqual(len(result), 0)
        with patch(
            "odoo.models.BaseModel.search",
            autospec=True,
            return_value=self.social_post_account_id,
        ) as mock_search:
            result = self.social_post_id.filter_by_media_types(
                [], [("message", "ilike", "Test")]
            )
            self.assertEqual(len(result), 1)
            mock_search.assert_called_once()

    def test_action_cancel(self):
        self.social_post_id.action_cancel()
        self.assertEqual(self.social_post_id.state, "cancelled")
        post_id = self.SocialPost.create(
            {
                "message": "Test",
                "account_ids": [(6, 0, [self.social_account_id.id])],
                "state": "publishing",
            }
        )
        with self.assertRaises(ValidationError):
            post_id.action_cancel()

    def test_prepare_post_account_values(self):
        other_account_id = self.SocialAccount.create(
            {
                "name": "Other Linkedin",
                "media_id": self.social_media_id.id,
            }
        )
        self.social_post_id.write(
            {
                "account_ids": [Command.link(other_account_id.id)],
            }
        )
        result = self.social_post_id._prepare_post_account_values()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][2]["account_id"], other_account_id.id)

    def test_get_result_none(self):
        result = self.WizardAccount._get_url_redirect()
        self.assertEqual(result, None)
        result = self.WizardAccount._action_add_account()
        self.assertEqual(result, None)
        result = self.WizardAccount._update_account()
        self.assertEqual(result, None)
        result = self.WizardAccount.update_account()
        self.assertEqual(result, None)
        result = self.WizardAccount._action_valid_add_account()
        self.assertTrue(result)