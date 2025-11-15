# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from unittest.mock import MagicMock, patch

from odoo.exceptions import ValidationError

from odoo.addons.social_media_base.tests.test_social_common import PATCH_POST_ACCOUNT
from odoo.addons.social_media_x.tests.test_common_x import (
    PATCH_ACCOUNT_X,
    TestSocialCommonX,
)


class TestSocialPostAccountX(TestSocialCommonX):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_response_errors = ["Error 1", "Error 2"]
        cls.post_data = {
            "body": "Test Comment",
            "attachment_ids": [1],
        }

    def create_test_comment(self):
        return self.SocialPostAccountX.create_x_comment(self.post_data)

    def test_create_comment(self):
        with patch.object(
            type(self.SocialPostAccountX), "create_x_comment"
        ) as mock_create_comment:
            self.SocialPostAccountX.create_comment(self.post_data)
            mock_create_comment.assert_called_once()

    def test_create_comment_super(self):
        with patch(PATCH_POST_ACCOUNT.format("create_comment")) as mock_create_comment:
            self.SocialPostAccount.create_comment(self.post_data)
            mock_create_comment.assert_called_once()

    def test_create_x_comment(self):
        mock_client = MagicMock()
        fake_client = MagicMock()
        fake_client.create_tweet.return_value = True
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with (
            mock_valid_time_request,
            mock_get_client_api as mock_client_api,
            patch.object(
                type(self.SocialAccountX),
                "_prepare_medias_for_tweet",
                return_value=mock_client,
            ) as mock_medias_for_tweet,
        ):
            res = self.create_test_comment()
            mock_medias_for_tweet.assert_called_once()
            mock_client_api.assert_called_once()
        self.assertTrue(res["success"])

        with (
            mock_valid_time_request,
            mock_get_client_api as mock_client_api,
        ):
            res_without_attach = self.SocialPostAccountX.create_x_comment(
                {
                    "body": self.test_message,
                }
            )
            mock_client_api.assert_called_once()
        self.assertTrue(res_without_attach["success"])

    def test_create_x_comment_exception(self):
        fake_client = MagicMock()
        fake_client.create_tweet.side_effect = Exception("Error Create Comment")
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            res = self.create_test_comment()
        self.assertFalse(res["success"])
        self.assertIn("Error Comment Tweet", res["message"])

    def test_create_x_comment_exception_manyrequests(self):
        fake_client = MagicMock()
        fake_client.create_tweet.return_value = False
        fake_client.create_tweet.side_effect = self.get_exception_manyrequests()
        (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests,
        ) = self.get_patch_exceptions_x(fake_client, True)
        with (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests as many_requests,
        ):
            self.create_test_comment()
        many_requests.assert_called_once()

    def test_compute_post_statistics_x(self):
        post_account_values = {
            "post_id": self.SocialPostX.id,
            "account_id": self.SocialAccountX.id,
            "message": "Message Test XX",
            "click_count": 5,
            "comment_count": 2,
            "retweet_count": 3,
            "quote_count": 2,
        }
        self.SocialPostAccount.create(post_account_values)
        post_account_values.update(
            {
                "message": "Message Test X",
                "click_count": 5,
                "comment_count": 1,
                "retweet_count": 5,
                "quote_count": 1,
            }
        )
        self.SocialPostAccount.create(post_account_values)
        expected = (5 + 5) + (2 + 1) + (3 + 5) + (2 + 1)
        self.assertEqual(self.SocialPostX.count_post_interactions, expected)

    @patch(PATCH_ACCOUNT_X.format("SocialAccount.get_client_api"))
    @patch(
        "odoo.addons.social_media_base.models.social_post_account.SocialPostAccount._delete_post_account"
    )
    @patch(PATCH_ACCOUNT_X.format("SocialAccount._valid_time_request"))
    def test_delete_post_account(
        self, mock_valid_time_request, mock_delete_post_account, mock_get_client_api
    ):
        mock_get_client_api.delete_tweet.return_value = True
        mock_valid_time_request.return_value = True
        self.SocialPostAccountX._delete_post_account()
        mock_delete_post_account.assert_called_once()

    def test_delete_post_account_exception(self):
        fake_client = MagicMock()
        fake_client.delete_tweet.side_effect = Exception("Error Delete Post")
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            with self.assertRaises(Exception) as ctx:
                self.SocialPostAccountX._delete_post_account()
            self.assertIn("Error Delete Post", str(ctx.exception))

    def test_delete_post_account_exception_manyrequests(self):
        fake_client = MagicMock()
        fake_client.delete_tweet.side_effect = self.get_exception_manyrequests()
        (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests,
        ) = self.get_patch_exceptions_x(fake_client, True)
        with (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests as many_requests,
        ):
            self.SocialPostAccountX._delete_post_account()
        many_requests.assert_called_once()

    def test_get_post_x(self):
        fake_response = MagicMock()
        fake_response.errors = False
        fake_client = MagicMock()
        fake_client.get_tweet.return_value = fake_response
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            res = self.SocialPostAccountX.get_post_x()
            self.assertTrue(res)

    def test_get_post_x_errors(self):
        res = self.SocialPostAccount.get_post_x()
        self.assertFalse(res)

        fake_response = MagicMock()
        fake_response.errors = self.test_response_errors
        fake_client = MagicMock()
        fake_client.get_tweet.return_value = fake_response
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            with self.assertRaises(ValidationError):
                self.SocialPostAccountX.get_post_x()

    def test_get_post_x_exception(self):
        fake_client = MagicMock()
        fake_client.get_tweet.side_effect = Exception("Error Get Comment")
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            with self.assertRaises(Exception) as ctx:
                self.SocialPostAccountX.get_post_x()
            self.assertIn("Error Get Comment", str(ctx.exception))

    def test_get_post_x_exception_manyrequests(self):
        fake_client = MagicMock()
        fake_client.get_tweet.return_value = False
        fake_client.get_tweet.side_effect = self.get_exception_manyrequests()
        (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests,
        ) = self.get_patch_exceptions_x(fake_client, True)
        with (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests as many_requests,
        ):
            self.SocialPostAccountX.get_post_x()
        many_requests.assert_called_once()

    def test_get_assets_save_x(self):
        fake_medias = ["media1"]
        media_map = {"media1": ("media_key1", "www.media_url_1", "media_type1")}
        attachment = self.env["ir.attachment"].create(
            {
                "name": "media_key1",
                "type": "binary",
                "res_model": self.SocialPostAccountX._name,
                "res_id": self.SocialPostAccountX.id,
                "datas": self.image_base64,
            }
        )
        with patch.object(
            type(self.SocialPostAccount),
            "_map_medias_account",
            autospec=True,
            return_value=attachment,
        ) as mock_map_medias:
            attachments = self.SocialPostAccountX._get_assets_save_x(
                fake_medias, media_map
            )
            self.assertEqual(len(attachments), 1)
            self.assertEqual(attachments[0]["type"], "binary")
            self.assertEqual(attachments[0]["res_model"], self.SocialPostAccountX._name)
            self.assertEqual(attachments[0]["res_id"], self.SocialPostAccountX.id)
            mock_map_medias.assert_called_once()

    def test_get_assets_save_x_failed(self):
        fake_medias = ["media1"]
        media_map = {"media1": ("media_key1", "www.media_url_1", "media_type1")}
        with patch.object(
            type(self.SocialPostAccount),
            "_get_medias_account",
            autospec=True,
            return_value=["media1"],
        ) as mock_get_medias:
            attachments = self.SocialPostAccountX._get_assets_save_x(
                fake_medias, media_map
            )
            self.assertEqual(len(attachments), 0)
            mock_get_medias.assert_called_once()

    def test_get_comments(self):
        now = datetime.now()
        fake_comment = MagicMock()
        fake_comment.id = "comment_id1"
        fake_comment.text = "Comment 1"
        fake_comment.author_id = "author_1"
        fake_comment.created_at = now
        fake_user = MagicMock()
        fake_user.id = "author_1"
        fake_user.created_at = now
        fake_user.profile_image_url = "https://www.fake.media/url_image"
        fake_response = MagicMock()
        fake_response.data = [fake_comment]
        fake_response.includes = {"users": [fake_user]}
        fake_response.errors = self.test_response_errors
        fake_client = MagicMock()
        fake_client.search_recent_tweets.return_value = fake_response
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            comments = self.SocialPostAccountX.get_comments()
            self.assertEqual(len(comments["data"]), 1)
            self.assertEqual(comments["data"][0]["id"], "comment_id1")
            self.assertEqual(comments["data"][0]["text"], "Comment 1")

    def test_get_comments_exception(self):
        fake_client = MagicMock()
        fake_client.search_recent_tweets.side_effect = Exception("Error Comments")
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            res = self.SocialPostAccountX.get_comments()
        self.assertFalse(res["success"])
        self.assertIn("Error Get Comments for Tweet", res["message"])

    def test_get_comments_exception_manyrequests(self):
        fake_client = MagicMock()
        fake_client.search_recent_tweets.side_effect = self.get_exception_manyrequests()
        (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests,
        ) = self.get_patch_exceptions_x(fake_client, True)
        with (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests as many_requests,
        ):
            self.SocialPostAccountX.get_comments()
        many_requests.assert_called_once()

    def test_action_post(self):
        self.SocialPostAccountX.write({"state": "ready"})
        with patch.object(
            type(self.SocialPostX),
            "filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountX,
        ) as mock_filter_by_media_types, patch.object(
            type(self.SocialPostAccountX.account_id),
            "create_tweet",
            autospec=True,
            return_value="122809890045",
        ) as mock_create_tweet:
            self.SocialPostAccountX._action_post(self.SocialPostX)
            self.assertEqual(self.SocialPostAccountX.x_post_account_id, "122809890045")
            self.assertEqual(self.SocialPostAccountX.state, "posted")
            self.assertIn(
                self.SocialPostAccountX.account_id.username,
                self.SocialPostAccountX.post_account_url,
            )
            mock_filter_by_media_types.assert_called_once()
            mock_create_tweet.assert_called_once()

    def test_action_post_failed(self):
        self.SocialPostAccountX.write({"state": "ready"})
        with patch.object(
            type(self.SocialPostX),
            "filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountX,
        ) as mock_filter_by_media_types, patch.object(
            type(self.SocialPostAccountX.account_id),
            "create_tweet",
            autospec=True,
            return_value=False,
        ) as mock_create_tweet:
            self.SocialPostAccountX._action_post(self.SocialPostX)
            self.assertEqual(self.SocialPostAccountX.state, "failed")
            mock_filter_by_media_types.assert_called_once()
            mock_create_tweet.assert_called_once()