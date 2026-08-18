# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytz

from odoo import Command
from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_ACCOUNT,
    PATCH_WIZARD_ACCOUNT,
)

from ..models.social_account import SocialAccount as SocialAccountXCls
from ..social_x_utils import _URL_PRICING_X
from ..wizards.wizard_social_account import (
    WizardSocialAccount as WizardSocialAccountXCls,
)
from .test_common_x import (
    PATCH_ACCOUNT_X,
    PATCH_REQUEST_POST,
    PATCH_WIZARD_ACCOUNT_X,
    TestSocialCommonX,
)

LOGGER_ACCOUNT_X = "odoo.addons.social_media_x.models.social_account"


class _FakeResponse:
    def __init__(self, headers):
        self.headers = headers


class _FakeException:
    def __init__(self, headers):
        self.response = _FakeResponse(headers)


class TestSocialAccountX(TestSocialCommonX):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @staticmethod
    def _b64(key, secret):
        return base64.b64encode(f"{key}:{secret}".encode()).decode("utf-8")

    @patch(PATCH_REQUEST_POST)
    def test_wizard_credentials_when_provided(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"access_token": "abc123"}
        mock_post.return_value = mock_resp
        wizard = SimpleNamespace(x_api_key="WZ_KEY", x_api_secret="WZ_SECRET")
        token = self.SocialAccountX._get_access_token_oauth2(
            wizard_social_account=wizard
        )
        self.assertEqual(token, "abc123")
        expected_headers = {
            "Authorization": f"Basic {self._b64('WZ_KEY', 'WZ_SECRET')}",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        }
        mock_post.assert_called_once_with(
            "https://api.twitter.com/oauth2/token",
            headers=expected_headers,
            data={"grant_type": "client_credentials"},
            timeout=10,
        )

    @patch(PATCH_REQUEST_POST)
    def test_credentials_when_wizard_missing(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"access_token": "xyz789"}
        mock_post.return_value = mock_resp
        wizard = SimpleNamespace(x_api_key=None, x_api_secret=None)
        token = self.SocialAccountCredentialX._get_access_token_oauth2(
            wizard_social_account=wizard
        )
        self.assertEqual(token, "xyz789")
        args, kwargs = mock_post.call_args
        self.assertEqual(
            kwargs["headers"]["Authorization"],
            f"Basic {self._b64('TEST_KEY', 'TEST_SECRET')}",
        )
        self.assertEqual(
            kwargs["headers"]["Content-Type"],
            "application/x-www-form-urlencoded;charset=UTF-8",
        )
        self.assertEqual(kwargs["data"], {"grant_type": "client_credentials"})
        self.assertEqual(kwargs["timeout"], 10)

    @patch(PATCH_REQUEST_POST)
    @patch(PATCH_ACCOUNT_X.format("_get_oauth"))
    def test_credentials_when_wizard_matches(self, mock_get_oauth, mock_post):
        self.WizardAccountX.write({"oauth_token": "wiz-token-123"})
        kwargs = {
            "oauth_token": "wiz-token-123",
            "oauth_verifier": "verif-xyz",
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = (
            "oauth_token=tok123&oauth_token_secret=sec456&user_id=1&screen_name=foo"
        )
        fake_auth = object()
        mock_get_oauth.return_value = fake_auth
        token, secret = self.SocialAccountCredentialX._get_access_token(kwargs)
        self.assertEqual(token, "tok123")
        self.assertEqual(secret, "sec456")
        mock_get_oauth.assert_called_once_with(
            "TEST_KEY", "TEST_SECRET", request_access_token=kwargs
        )
        mock_post.assert_called_once_with(
            "https://api.twitter.com/oauth/access_token",
            auth=fake_auth,
            data={"oauth_verifier": "verif-xyz"},
            timeout=10,
        )

    @patch(PATCH_REQUEST_POST)
    @patch(PATCH_ACCOUNT_X.format("_get_oauth"))
    def test_rejects_request_token_without_wizard(self, mock_get_oauth, mock_post):
        kwargs = {
            "oauth_token": "no-match-token",
            "oauth_verifier": "verif-abc",
        }
        with self.assertRaises(UserError):
            self.SocialAccountCredentialX._get_access_token(kwargs)
        mock_get_oauth.assert_not_called()
        mock_post.assert_not_called()

    def test_rejects_callback_without_request_token(self):
        with self.assertRaises(UserError):
            self.SocialAccountCredentialX._get_access_token({"oauth_verifier": "v"})

    def test_rejects_request_token_of_another_user(self):
        self.WizardAccountX.write({"oauth_token": "wiz-token-123"})
        other_user = self.env["res.users"].create(
            {
                "name": "Other social user",
                "login": "other_social_user_x_test",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "social_media_base.group_social_media_user"
                            ).id,
                        ],
                    )
                ],
            }
        )
        with self.assertRaises(UserError):
            self.SocialAccountCredentialX.with_user(other_user)._get_access_token(
                {"oauth_token": "wiz-token-123", "oauth_verifier": "v"}
            )

    @patch(PATCH_ACCOUNT_X.format("tweepy.Client"))
    def test_client_mode_wizard_when_has_no_keys(self, mock_tweepy_client):
        self.WizardAccountX.write(
            {
                "oauth_token": "wiztok-1",
            }
        )
        result = self.SocialAccountEmptyX.get_client_api(
            client_api=True,
            bearer_token="BT_PARAM",
            kwargs={"oauth_token": "wiztok-1"},
        )
        self.assertIs(result, mock_tweepy_client.return_value)
        mock_tweepy_client.assert_called_once_with(
            bearer_token="BT_PARAM",
            consumer_key="TEST_KEY",
            consumer_secret="TEST_SECRET",
            access_token=False,
            access_token_secret=False,
        )

    @patch(PATCH_ACCOUNT_X.format("tweepy.Client"))
    def test_client_mode_prefers_self_over_wizard(self, mock_tweepy_client):
        account = self.SocialAccount.create(
            {
                "name": "Twitter2",
                "x_api_key": "SELF_KEY",
                "x_api_secret": "SELF_SECRET",
                "x_access_token_oauth2": "BT_SELF",
                "x_access_token_oauth1": "AT_SELF",
                "x_access_secret_oauth1": "AS_SELF",
            }
        )
        self.WizardAccountX.write(
            {
                "oauth_token": "wiztok-2",
            }
        )
        result = account.get_client_api(
            client_api=True,
            bearer_token="BT_PARAM_SHOULD_BE_IGNORED",
            kwargs={"oauth_token": "wiztok-2"},
        )
        self.assertIs(result, mock_tweepy_client.return_value)
        mock_tweepy_client.assert_called_once_with(
            bearer_token="BT_SELF",
            consumer_key="SELF_KEY",
            consumer_secret="SELF_SECRET",
            access_token="AT_SELF",
            access_token_secret="AS_SELF",
        )

    @patch(PATCH_ACCOUNT_X.format("tweepy.API"))
    @patch(PATCH_ACCOUNT_X.format("tweepy.OAuth1UserHandler"))
    def test_non_client_mode_uses_oauth1_flow(self, mock_oauth1_handler, mock_api):
        account = self.SocialAccount.create(
            {
                "name": "Twitter3",
                "x_api_key": "SELF_KEY",
                "x_api_secret": "SELF_SECRET",
                "x_access_token_oauth1": "AT_SELF",
                "x_access_secret_oauth1": "AS_SELF",
            }
        )
        result = account.get_client_api(
            client_api=False,
            x_access_token_oauth1=None,
            x_access_secret_oauth1=None,
        )
        mock_oauth1_handler.assert_called_once_with(
            consumer_key="SELF_KEY",
            consumer_secret="SELF_SECRET",
            access_token="AT_SELF",
            access_token_secret="AS_SELF",
        )
        mock_api.assert_called_once_with(mock_oauth1_handler.return_value)
        self.assertIs(result, mock_api.return_value)

    def _fake_api(self, captured):
        class _FakeAPI:
            def __init__(self, cap):
                self.cap = cap
                self.counter = 0

            def media_upload(self, filename, file):
                data = file.read()
                self.cap.append((filename, data))
                self.counter += 1
                return type("FakeMedia", (), {"media_id": 100 + self.counter})

        return _FakeAPI(captured)

    def test_handles_empty_list(self):
        captured_calls = []
        fake_api = self._fake_api(captured_calls)
        with patch.object(
            type(self.SocialAccount), "get_client_api", return_value=fake_api
        ) as mock_get:
            media_ids = self.SocialAccount._prepare_medias_for_tweet(
                image_ids=[], video_ids=[]
            )
        self.assertEqual(media_ids, [])
        self.assertEqual(captured_calls, [])
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs, {"client_api": False})

    def _patch_super(self, record, return_value):
        return self.get_patch_super_x(
            record,
            WizardSocialAccountXCls,
            "_action_valid_add_account",
            return_value=return_value,
        )

    def test_media_type_x_account(self):
        # The wizard carries the credentials of SocialAccountCredentialX, so
        # the duplicate check of the x branch must reject it.
        with (
            self._patch_super(
                self.WizardAccountX, return_value="SUPER_OK"
            ) as mock_super,
            self.assertRaises(UserError),
        ):
            self.WizardAccountX._action_valid_add_account()
        mock_super.assert_called_once_with()

        self.WizardAccountX.write(
            {
                "x_api_key": "TEST_FAKE_KEY",
                "x_api_secret": "TEST_FAKE_SECRET",
            }
        )
        with self._patch_super(self.WizardAccountX, return_value=False) as mock_super:
            res = self.WizardAccountX._action_valid_add_account()
        mock_super.assert_called_once_with()
        self.assertFalse(res)

        with self._patch_super(self.WizardAccountX, return_value=True) as mock_super:
            res = self.WizardAccountX._action_valid_add_account()
        mock_super.assert_called_once_with()
        self.assertTrue(res)

    def _patch_super_update(self, record, return_action):
        return self.get_patch_super_x(
            record,
            SocialAccountXCls,
            "update_account",
            return_value=return_action,
        )

    def test_media_type_x_existing_context(self):
        super_action = {
            "type": "ir.actions.act_window",
            "context": {
                "keep": True,
                "another": 1,
                "default_x_api_key": "DEF_TEST_KEY",
                "default_x_api_secret": "DEF_TEST_SECRET",
            },
        }
        with self._patch_super_update(
            self.SocialAccountCredentialX, super_action
        ) as mock_super:
            res = self.SocialAccountCredentialX.update_account()
        mock_super.assert_called_once_with()
        self.assertIsInstance(res, dict)
        self.assertIn("context", res)
        self.assertTrue(res["context"].get("keep"))
        self.assertEqual(res["context"].get("another"), 1)
        self.assertEqual(res["context"]["default_x_api_key"], "TEST_KEY")
        self.assertEqual(res["context"]["default_x_api_secret"], "TEST_SECRET")

    @patch(PATCH_REQUEST_POST)
    @patch(PATCH_WIZARD_ACCOUNT_X.format("_get_oauth"))
    def test_success_returns_act_url_and_sets_token(self, mock_get_oauth, mock_post):
        mock_get_oauth.return_value = object()
        mock_post.return_value = Mock(
            status_code=200, text="oauth_token=AAA&oauth_token_secret=BBB"
        )
        res = self.WizardAccountX._get_url_authorize()
        mock_get_oauth.assert_called_once_with("TEST_KEY", "TEST_SECRET")
        mock_post.assert_called_once_with(
            "https://api.twitter.com/oauth/request_token",
            auth=mock_get_oauth.return_value,
            timeout=10,
        )
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("type"), "ir.actions.act_url")
        self.assertEqual(res.get("target"), "self")
        self.assertIn("url", res)
        self.assertTrue(
            res["url"].startswith("https://api.twitter.com/oauth/authorize?")
        )
        self.assertIn("oauth_token=AAA", res["url"])
        self.assertEqual(self.WizardAccountX.oauth_token, "AAA")

    @patch(PATCH_WIZARD_ACCOUNT_X.format("_logger"))
    @patch(PATCH_REQUEST_POST)
    @patch(PATCH_WIZARD_ACCOUNT_X.format("_get_oauth"))
    def test_valueerror_returns_notification(
        self, mock_get_oauth, mock_post, mock_logger
    ):
        mock_get_oauth.return_value = object()
        mock_post.return_value = Mock(text="oauth_token")
        res = self.WizardAccountX._get_url_authorize()
        mock_logger.error.assert_called()
        self.assertEqual(res.get("type"), "ir.actions.client")
        self.assertEqual(res.get("tag"), "display_notification")
        self.assertEqual(res.get("target"), "new")
        params = res.get("params", {})
        self.assertEqual(params.get("type"), "danger")
        self.assertFalse(params.get("sticky"))
        self.assertEqual(params.get("next"), {"type": "ir.actions.act_window_close"})
        self.assertTrue(params.get("message"))

    @patch(PATCH_WIZARD_ACCOUNT_X.format("_logger"))
    @patch(PATCH_REQUEST_POST)
    @patch(PATCH_WIZARD_ACCOUNT_X.format("_get_oauth"))
    def test_not_enrolled_app_explains_the_paid_plan(
        self, mock_get_oauth, mock_post, mock_logger
    ):
        mock_get_oauth.return_value = object()
        mock_post.return_value = Mock(
            status_code=403,
            text='{"errors":[{"reason":"client-not-enrolled"}]}',
        )
        res = self.WizardAccountX._get_url_authorize()
        params = res.get("params", {})
        self.assertIn("not enrolled in a paid plan", params.get("message", ""))
        # ``display_notification`` escapes the message, so the link is passed
        # apart instead of being written in it.
        self.assertEqual(
            params.get("links"),
            [{"url": _URL_PRICING_X, "label": "X API pricing"}],
        )

    def test_app_not_attached_to_a_project_explains_the_paid_plan(self):
        """The API v2 endpoints do not answer ``client-not-enrolled``."""
        error = Exception(
            "403 Forbidden\nWhen authenticating requests to the X API v2 "
            "endpoints, you must use keys and tokens from a developer App "
            "that is attached to a Project. You can create a project via the "
            "developer portal."
        )
        message = self.SocialAccount._x_error_message(error)
        self.assertIn("not enrolled in a paid plan", message)
        self.assertIn(_URL_PRICING_X, message)

    def test_x_error_message_keeps_other_errors(self):
        self.assertEqual(
            self.SocialAccount._x_error_message(ValueError("Some other error")),
            "Some other error",
        )

    def test_x_error_message_escapes_the_answer_of_x(self):
        """The answer of X is third party content and it is not markup."""
        message = self.SocialAccount._x_error_message(
            ValueError("<script>alert(1)</script>")
        )
        self.assertNotIn("<script>", message)
        self.assertIn("&lt;script&gt;", message)

    def _fake_client(self, user_id="ID123", name="User Name", username="user"):
        me = SimpleNamespace(
            data=SimpleNamespace(id=user_id, name=name, username=username)
        )
        client = Mock()
        client.get_me.return_value = me
        return client

    def test_update_account_data(self):
        fake_client = MagicMock()
        fake_data = fake_client.get_me.return_value.data
        fake_data.name = "Account Name X"
        fake_data.username = "account-username-x"
        fake_data.profile_image_url = "https://example.com/img_url"
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.content = b"fake-image-bytes"
        with (
            patch.object(
                type(self.social_account_id),
                "get_client_api",
                autospec=True,
                return_value=fake_client,
            ) as mock_get_client_api,
            patch(
                PATCH_ACCOUNT_X.format("requests.get"),
                autospec=True,
                return_value=fake_response,
            ) as mock_get,
            patch.object(
                type(self.social_account_id),
                "write",
                autospec=True,
            ) as mock_write,
        ):
            self.social_account_id._update_account_data()
            mock_get_client_api.assert_called_once()
            mock_get.assert_called_once()
        # Asserted on the written values: image_1920 has a default avatar, so
        # reading the field back cannot tell an update apart from no update.
        mock_write.assert_called_once()
        self.assertEqual(
            mock_write.call_args.args[1],
            {
                "name": "Account Name X",
                "username": "account-username-x",
                "image_1920": base64.b64encode(b"fake-image-bytes"),
            },
        )

    def test_update_account_data_without_image(self):
        """A failed download leaves the current avatar untouched."""
        fake_client = MagicMock()
        fake_data = fake_client.get_me.return_value.data
        fake_data.name = "Account Name X"
        fake_data.username = "account-username-x"
        fake_data.profile_image_url = "https://example.com/img_url"
        fake_response = MagicMock()
        fake_response.status_code = 404
        with (
            patch.object(
                type(self.social_account_id),
                "get_client_api",
                autospec=True,
                return_value=fake_client,
            ),
            patch(
                PATCH_ACCOUNT_X.format("requests.get"),
                autospec=True,
                return_value=fake_response,
            ),
            patch.object(
                type(self.social_account_id),
                "write",
                autospec=True,
            ) as mock_write,
        ):
            self.social_account_id._update_account_data()
        mock_write.assert_called_once()
        self.assertEqual(
            mock_write.call_args.args[1],
            {"name": "Account Name X", "username": "account-username-x"},
        )

    def test_wizard_update_account(self):
        with patch(
            PATCH_WIZARD_ACCOUNT.format("_update_account")
        ) as mock_updt_account_super:
            self.WizardAccount._update_account()
            mock_updt_account_super.assert_called_once()

        with (
            patch.object(
                type(self.WizardAccountX.account_id), "_update_account_data"
            ) as mock_update_account_data,
            patch(
                PATCH_WIZARD_ACCOUNT.format("_update_account")
            ) as mock_update_account_super,
        ):
            self.WizardAccountX._update_account()
            mock_update_account_data.assert_called_once()
            mock_update_account_super.assert_called_once()

        fake_url = {
            "type": "ir.actions.act_url",
            "url": "https://example.com",
            "target": "self",
        }
        self.WizardAccountX.write({"update_keys": True})
        with patch.object(
            type(self.WizardAccountX), "_get_url_authorize", return_value=fake_url
        ):
            result = self.WizardAccountX._update_account()
            self.assertEqual(result["type"], "ir.actions.act_url")
            self.assertEqual(result["url"], "https://example.com")
            self.assertEqual(result["target"], "self")

    def test_wizard_action_valid_add_account(self):
        wizard_id = self.WizardAccount.create(
            {
                "x_api_key": "TEST_KEY1",
                "x_api_secret": "TEST_SECRET1",
                "media_id": self.media_x_id.id,
            }
        )
        result = wizard_id._action_valid_add_account()
        self.assertTrue(result)

        wizard_id.write({"x_api_key": "TEST_KEY", "x_api_secret": "TEST_SECRET"})
        with self.assertRaises(UserError):
            wizard_id._action_valid_add_account()

    def test_onchange_post_since_id(self):
        self.SocialAccountX._onchange_post_since_id()
        self.assertFalse(self.SocialAccountX.post_since_id)
        self.assertFalse(self.SocialAccountX.last_post_id)

    def test_compute_post_since_id(self):
        account_id = self.SocialAccount.create(
            {
                "name": "Test account X",
                "media_id": self.media_x_id.id,
                "enable_since": True,
            }
        )
        post_id = self.SocialPost.create(
            {
                "message": "Test Message Enable Since",
                "account_ids": [Command.set(account_id.ids)],
            }
        )
        post_account_values = {
            "post_id": post_id.id,
            "account_id": account_id.id,
            "message": "Message Test XX",
            "click_count": 5,
            "comment_count": 2,
            "retweet_count": 3,
            "quote_count": 2,
        }
        post_account_id = self.SocialPostAccount.create(post_account_values)
        self.assertEqual(account_id.post_since_id, post_account_id)

        account_id.write({"enable_since": False})
        self.assertFalse(
            account_id.post_since_id,
            msg="Turning the option off by write must clear the stored post.",
        )
        account_id.write({"enable_since": True})
        self.assertEqual(account_id.post_since_id, post_account_id)

        account_id.write({"last_post_id": post_account_id.id})
        self.assertEqual(int(account_id.last_post_id), post_account_id.id)

    def test_get_message_many_requests(self):
        self.social_account_id.write({"rate_limit_endpoint": False})
        with patch.object(
            type(self.social_account_id), "_notify_user_client", autospec=True
        ) as mocked_notify:
            res = self.social_account_id._get_message_many_requests(
                ex=None, endpoint="get_tweets", view_type="kanban"
            )
            self.assertTrue(res)
            mocked_notify.assert_not_called()
        fixed_reset = 1735689600
        ex = _FakeException(
            {
                "x-rate-limit-limit": "50",
                "x-rate-limit-remaining": "0",
                "x-rate-limit-reset": str(fixed_reset),
            }
        )
        self.social_account_id.write({"rate_limit_endpoint": False})
        with patch.object(
            type(self.social_account_id), "_notify_user_client", autospec=True
        ) as mocked_notify:
            res = self.social_account_id._get_message_many_requests(
                ex=ex, endpoint="get_tweets", view_type="kanban"
            )
            self.assertFalse(res)
            stored = self.social_account_id.rate_limit_endpoint.get("get_tweets")
            self.assertEqual(stored["x-rate-limit-limit"], 50)
            self.assertEqual(stored["x-rate-limit-remaining"], 0)
            self.assertEqual(stored["x-rate-limit-reset"], fixed_reset)
            mocked_notify.assert_called_once()
            _, kwargs = mocked_notify.call_args
            self.assertEqual(kwargs["notif_type"], "social_kanban_info")
            self.assertEqual(kwargs["media"], "X")
            self.assertEqual(kwargs["account_name"], self.social_account_id.name)
            notif_message = kwargs["notif_message"]
            self.assertIn("Get tweets", notif_message)
            self.assertIn("Total limit:", notif_message)
            self.assertIn("Remaining:", notif_message)
            self.assertIn("rate limits", notif_message)
            self.assertIn(
                "https://docs.x.com/x-api/fundamentals/rate-limits", notif_message
            )
        fixed_reset = 1735689600
        ex = _FakeException(
            {
                "x-rate-limit-limit": "10",
                "x-rate-limit-remaining": "1",
                "x-rate-limit-reset": str(fixed_reset),
            }
        )
        self.social_account_id.write({"rate_limit_endpoint": False})
        with patch.object(
            type(self.social_account_id), "_notify_user_client", autospec=True
        ) as mocked_notify:
            res = self.social_account_id._get_message_many_requests(
                ex=ex, endpoint="get_users_tweets", view_type="list"
            )
            self.assertFalse(res)
            _, kwargs = mocked_notify.call_args
            self.assertEqual(kwargs["notif_type"], "social_list_info")
            self.assertIn("Get users tweets", kwargs["notif_message"])

    def test_action_add_account(self):
        wizard = self.WizardAccountX
        wizard.media_type = "x"
        with (
            patch(
                "odoo.addons.social_media_x.wizards.wizard_social_account."
                "WizardSocialAccount._get_url_authorize",
                autospec=True,
                return_value={"type": "ir.actions.act_url"},
            ) as mock_get_url,
            patch(
                "odoo.addons.social_media_base.wizards.wizard_social_account."
                "WizardSocialAccount._action_add_account",
                autospec=True,
                return_value={"super": True},
            ) as mock_super,
        ):
            result = wizard._action_add_account()

            mock_super.assert_called_once()
            mock_get_url.assert_called_once()
            self.assertEqual(result, {"type": "ir.actions.act_url"})
        with patch(
            "odoo.addons.social_media_base.wizards.wizard_social_account."
            "WizardSocialAccount._action_add_account",
            autospec=True,
            return_value={"super": True},
        ) as mock_add_super:
            self.WizardAccount._action_add_account()
            mock_add_super.assert_called_once()

    def test_valid_time_request(self):
        date_end = datetime.now() + timedelta(hours=1)
        self.social_account_id.rate_limit_endpoint = {
            "get_tweets": {
                "x-rate-limit-reset": int(date_end.timestamp()),
            }
        }
        with patch.object(
            type(self.social_account_id),
            "_get_message_many_requests",
            autospec=True,
            return_value=False,
        ) as mock_get_message_many_requests:
            res = self.social_account_id._valid_time_request()
            self.assertFalse(res)
            mock_get_message_many_requests.assert_called_once()

        self.social_account_id.rate_limit_endpoint = False
        res = self.social_account_id._valid_time_request()
        self.assertTrue(res)

    @mute_logger(LOGGER_ACCOUNT_X)
    def test_create_account_x(self):
        self.WizardAccountX.write({"oauth_token": "wiz-token-create"})
        callback_kwargs = {"oauth_token": "wiz-token-create"}
        fake_client = MagicMock()
        fake_client.get_me.return_value.data.id = "12345"
        fake_client.get_me.return_value.data.name = "Juan X"
        fake_client.get_me.return_value.data.username = "juanX"
        fake_client.get_me.return_value.data.profile_image_url = (
            "https://example.com/img_url"
        )
        fake_response = MagicMock()
        fake_response.status_code = 404
        fake_response.content = b"fake-image-bytes"
        patch_get_client_api = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with (
            patch_get_client_api as mock_get_client_api,
            patch(
                PATCH_ACCOUNT_X.format("requests.get"),
                autospec=True,
                return_value=fake_response,
            ) as mock_get,
            patch.object(
                type(self.SocialAccount),
                "_get_access_token_oauth2",
                autospec=True,
                return_value="fake_access_token_oauth2",
            ) as mock_get_access_token_oauth2,
            patch.object(
                type(self.SocialAccount),
                "_trigger_initial_sync",
                autospec=True,
            ) as mock_trigger_sync,
        ):
            self.SocialAccount.create_account_x(
                "x_access_token_oauth1", "x_access_secret_oauth1", callback_kwargs
            )
            mock_get_client_api.assert_called_once()
            mock_get.assert_called_once()
            mock_get_access_token_oauth2.assert_called_once()
            mock_trigger_sync.assert_called_once()

        patch_get_client_api = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with (
            patch_get_client_api as mock_get_client_api,
            patch(
                PATCH_ACCOUNT_X.format("requests.get"),
                autospec=True,
                return_value=fake_response,
            ) as mock_get,
            patch.object(
                type(self.SocialAccount),
                "_get_access_token_oauth2",
                autospec=True,
                return_value=False,
            ) as mock_get_access_token_oauth2,
            patch.object(
                type(self.SocialAccount),
                "_notify_user_session",
                autospec=True,
                return_value=False,
            ) as mock_notify_user_session,
        ):
            self.SocialAccount.create_account_x(
                "x_access_token_oauth1", "x_access_secret_oauth1", callback_kwargs
            )
            mock_get_client_api.assert_called_once()
            mock_get.assert_called_once()
            mock_get_access_token_oauth2.assert_called_once()
            mock_notify_user_session.assert_called_once()

    def test_create_account_x_reactivates_archived(self):
        self.WizardAccountX.write({"oauth_token": "wiz-token-create"})
        callback_kwargs = {"oauth_token": "wiz-token-create"}
        self.SocialAccount.create(
            {
                "name": "Archived X",
                "username": "archived-x-user",
                "media_id": self.env.ref("social_media_x.social_media_x").id,
                "active": False,
            }
        )
        fake_client = MagicMock()
        fake_client.get_me.return_value.data.id = "54321"
        fake_client.get_me.return_value.data.name = "Archived X"
        fake_client.get_me.return_value.data.username = "archived-x-user"
        fake_client.get_me.return_value.data.profile_image_url = (
            "https://example.com/img_url"
        )
        fake_response = MagicMock()
        fake_response.status_code = 404
        patch_get_client_api = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with (
            patch_get_client_api,
            patch(
                PATCH_ACCOUNT_X.format("requests.get"),
                autospec=True,
                return_value=fake_response,
            ),
            patch.object(
                type(self.SocialAccount),
                "_get_access_token_oauth2",
                autospec=True,
                return_value="fake_access_token_oauth2",
            ),
            patch.object(
                type(self.SocialAccount),
                "_trigger_initial_sync",
                autospec=True,
            ),
        ):
            self.SocialAccount.create_account_x(
                "x_access_token_oauth1", "x_access_secret_oauth1", callback_kwargs
            )
        accounts = self.SocialAccount.with_context(active_test=False).search(
            [("username", "=", "archived-x-user"), ("media_type", "=", "x")]
        )
        self.assertEqual(len(accounts), 1)
        self.assertTrue(accounts.active)

    def test_create_account_x_exception_manyrequests(self):
        fake_client = MagicMock()
        fake_client.get_me.side_effect = self.get_exception_manyrequests()
        (
            mock_get_client_api,
            mock_many_requests,
        ) = self.get_patch_exceptions_x(fake_client, True, valid_time_request=False)
        with (
            mock_get_client_api,
            mock_many_requests as many_requests,
        ):
            self.SocialAccount.create_account_x(
                "x_access_token_oauth1", "x_access_secret_oauth1", {}
            )
        many_requests.assert_called_once()

    @mute_logger(LOGGER_ACCOUNT_X)
    def test_create_account_x_error_survives_the_callback_redirect(self):
        """The message is kept in the session, and only there.

        The callback answers with a redirect that reloads the web client, so
        a bus notification races with it: it is either lost or shown next to
        the one of the session.
        """
        fake_client = MagicMock()
        fake_client.get_me.side_effect = Exception(
            "403 Forbidden\nWhen authenticating requests to the X API v2 "
            "endpoints, you must use keys and tokens from a developer App "
            "that is attached to a Project."
        )
        patch_get_client_api = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with (
            patch_get_client_api,
            patch.object(
                type(self.SocialAccount),
                "_notify_user_session",
                autospec=True,
            ) as mock_session,
            patch.object(
                type(self.SocialAccount),
                "_notify_user_client",
                autospec=True,
            ) as mock_client,
        ):
            self.SocialAccount.create_account_x(
                "x_access_token_oauth1", "x_access_secret_oauth1", {}
            )
        mock_session.assert_called_once()
        mock_client.assert_not_called()
        message = mock_session.call_args[0][1]
        self.assertIn("not enrolled in a paid plan", message)
        self.assertIn(_URL_PRICING_X, message)
        self.assertIn("Social Media X", message)

    def test_create_tweet(self):
        fake_client = MagicMock()
        fake_client.create_tweet.return_value.data = {"id": "tweet_idX"}
        patch_get_client_api = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with (
            patch_get_client_api as mock_get_client_api,
            patch.object(
                type(self.SocialAccount),
                "_prepare_medias_for_tweet",
                autospec=True,
                return_value=[],
            ) as mock_prepare_medias_for_tweet,
        ):
            res = self.SocialAccount.create_tweet("Message Test", [], [], None, {})
            self.assertEqual(res, "tweet_idX")
            mock_get_client_api.assert_called_once()
            mock_prepare_medias_for_tweet.assert_called_once()

    def test_create_tweet_exception_manyrequests(self):
        fake_client = MagicMock()
        fake_client.create_tweet.side_effect = self.get_exception_manyrequests()
        (
            mock_get_client_api,
            mock_many_requests,
        ) = self.get_patch_exceptions_x(fake_client, True, valid_time_request=False)
        with (
            mock_get_client_api,
            mock_many_requests as many_requests,
        ):
            self.SocialAccount.create_tweet("Message Test", [], [], None, {})
        many_requests.assert_called_once()

    @mute_logger(LOGGER_ACCOUNT_X)
    def test_create_tweet_exception(self):
        fake_client = MagicMock()
        fake_client.create_tweet.side_effect = Exception("Error message")
        mock_get_client_api = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with (
            mock_get_client_api,
            patch.object(
                type(self.social_account_id), "_notify_user_client", autospec=True
            ) as mocked_notify,
        ):
            self.SocialAccount.create_tweet("Message Test", [], [], None, {})
        mocked_notify.assert_called_once()

    def test_get_users_tweets(self):
        fake_client = MagicMock()
        fake_client.get_users_tweets.return_value.includes = {
            "media": [self.image_base64]
        }
        patch_get_client_api = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with (
            patch_get_client_api as mock_get_client_api,
        ):
            res = self.SocialAccountX._get_users_tweets()
            self.assertEqual(len(res.includes.get("media")), 1)
        mock_get_client_api.assert_called_once()
        _, kwargs = fake_client.get_users_tweets.call_args
        self.assertEqual(kwargs["id"], self.SocialAccountX.remote_ref)
        self.assertEqual(kwargs["max_results"], 100)

    def test_get_public_metrics(self):
        mock_public_metrics = MagicMock()
        mock_public_metrics.public_metrics = {
            "like_count": 5,
            "reply_count": 10,
            "retweet_count": 15,
            "quote_count": 20,
            "impression_count": 40,
        }
        res = self.SocialAccountX._get_public_metrics(mock_public_metrics)
        self.assertEqual(res[0], 5)
        self.assertEqual(res[1], 40)
        self.assertEqual(res[2], 10)
        self.assertEqual(res[3], 15)
        self.assertEqual(res[4], 20)

    def test_get_x_statistics(self):
        statistics = ["Test", 1, 1, 10, 11, 12, 13]
        rows = [{"id": self.SocialAccountX.id, "name": "X Account"}]
        with patch(
            "odoo.models.BaseModel.search_read", autospec=True, return_value=rows
        ) as mock_search_read:
            res = self.SocialAccountX._get_x_statistics(statistics)
        mock_search_read.assert_called_once()
        self.assertEqual(res, statistics + rows)
        self.assertIn(("media_type", "=", "x"), mock_search_read.call_args.args[1])

    def test_update_posts_statistics(self):
        patch_super = patch(PATCH_ACCOUNT.format("_update_posts_statistics"))
        patch_get_statistics = patch.object(
            type(self.SocialAccount),
            "_get_x_statistics",
            autospec=True,
            return_value=None,
        )
        fake_client = MagicMock()
        fake_client.get_users_tweets.return_value.includes = {
            "media": [
                MagicMock(
                    media_key="media_key_tests",
                    url="https://media_url_tests",
                    type="image",
                )
            ],
            "users": [MagicMock(id="author_12345", username="username-idx")],
        }
        tweet_created_at = datetime(2026, 1, 15, 10, 30, tzinfo=pytz.utc)
        fake_tweet = MagicMock(
            referenced_tweets=[MagicMock(type="fake_quoted")],
            in_reply_to_user_id=None,
            conversation_id="conversation_12345",
            id="conversation_12345",
            author_id="author_12345",
            text="Tweet text https://t.co/short",
            created_at=tweet_created_at,
            attachments={"media_keys": ["media_key_tests"]},
            entities={"urls": [{"url": "https://t.co/short"}]},
        )
        fake_tweet.get.return_value = "conversation_12345"
        fake_client.get_users_tweets.return_value.data = [fake_tweet]
        patch_get_users_tweets = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )

        search_side_effect = self.get_search_side_effect_x()

        with (
            patch_super as mock_update_posts_statistics_super,
            patch(
                "odoo.models.BaseModel.search",
                autospec=True,
                side_effect=search_side_effect,
            ) as mock_search,
            patch.object(
                type(self.SocialAccount),
                "_valid_time_request",
                autospec=True,
                return_value=True,
            ) as mock_valid_time_request,
            patch.object(
                type(self.SocialPostAccountX),
                "_get_assets_save_x",
                autospec=True,
                return_value=[Command.create({"name": "media_key_tests"})],
            ) as mock_get_assets_save_x,
            patch.object(
                type(self.SocialAccount),
                "_get_public_metrics",
                autospec=True,
                return_value=(5, 10, 15, 20, 25),
            ) as mock_get_public_metrics,
            patch_get_users_tweets as mock_get_users_tweets,
            patch_get_statistics as mock_get_statistics,
        ):
            self.SocialAccount._update_posts_statistics(None, [])

            mock_update_posts_statistics_super.assert_called_once()
            self.assertEqual(
                self._count_search_calls(
                    mock_search,
                    model="social.account",
                    domain_leaf=("media_type", "=", "x"),
                ),
                1,
                msg="One social.account search for the x media type.",
            )
            self.assertEqual(
                self._count_search_calls(mock_search, model="social.post.account"),
                1,
                msg="One search to prefetch the post accounts of the tweet.",
            )
            mock_valid_time_request.assert_called_once()
            mock_get_users_tweets.assert_called_once()
            mock_get_assets_save_x.assert_called_once()
            mock_get_public_metrics.assert_called_once()
            mock_get_statistics.assert_called_once()

        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(
            self.SocialAccountX.like_count,
            5,
            msg="Read back from the database so a silently swallowed write "
            "cannot make the assertions pass from the ORM cache.",
        )
        self.assertEqual(self.SocialAccountX.impression_count, 10)
        self.assertEqual(self.SocialAccountX.comment_count, 15)
        self.assertEqual(self.SocialAccountX.retweet_count, 20)
        self.assertEqual(self.SocialAccountX.quote_count, 25)

        post_account = self.SocialAccountX.post_account_ids.filtered(
            lambda post: post.remote_ref == "conversation_12345"
        )
        self.assertEqual(len(post_account), 1)
        self.assertEqual(post_account.message, "Tweet text ")
        self.assertEqual(post_account.author, self.SocialAccountX.name)
        self.assertEqual(post_account.actor_urn, "author_12345")
        self.assertEqual(post_account.state, "posted")
        user_timezone = pytz.timezone(self.env.user.tz or "UTC")
        self.assertEqual(
            post_account.published_date,
            tweet_created_at.astimezone(user_timezone).replace(tzinfo=None),
        )
        self.assertEqual(post_account.image_ids.mapped("name"), ["media_key_tests"])

    def test_update_posts_statistics_empty(self):
        patch_super = patch(PATCH_ACCOUNT.format("_update_posts_statistics"))
        patch_get_statistics = patch.object(
            type(self.SocialAccount),
            "_get_x_statistics",
            autospec=True,
            return_value=None,
        )

        with (
            patch_super as mock_update_posts_statistics_super,
            patch_get_statistics as mock_get_statistics,
        ):
            self.social_account_id._update_posts_statistics(None, [])
            mock_update_posts_statistics_super.assert_called_once()
            mock_get_statistics.assert_called_once()

    def test_update_account(self):
        def super_action():
            # Rebuilt per block: the x branch writes back into this very dict.
            return {
                "type": "ir.actions.act_window",
                "context": {"from_super": True},
            }

        # An x account always gets the credential defaults, even when empty.
        with self._patch_super_update(
            self.SocialAccountX, super_action()
        ) as mock_update_account_super:
            res = self.SocialAccountX.update_account()
        mock_update_account_super.assert_called_once()
        self.assertTrue(res["context"]["from_super"])
        self.assertFalse(res["context"]["default_x_api_key"])
        self.assertFalse(res["context"]["default_x_api_secret"])

        # Outside the x media type the super result is returned untouched.
        with self._patch_super_update(
            self.SocialAccount, super_action()
        ) as mock_update_account_super:
            res_empty = self.SocialAccount.update_account()
        mock_update_account_super.assert_called_once()
        self.assertEqual(res_empty["context"], {"from_super": True})

    def test_get_chart_account_statistics_empty(self):
        patch_super = patch(PATCH_ACCOUNT.format("_get_chart_account_statistics"))
        with (
            patch(
                "odoo.models.BaseModel.search", autospec=True, return_value=[]
            ) as mock_search,
            patch_super as mock_super,
        ):
            self.SocialAccount._get_chart_account_statistics(None, None, None)
            self.assertEqual(
                self._count_search_calls(
                    mock_search,
                    model="social.account",
                    domain_leaf=("media_type", "=", "x"),
                ),
                1,
            )
            mock_super.assert_called_once()

    def test_get_chart_account_statistics(self):
        patch_super = patch(PATCH_ACCOUNT.format("_get_chart_account_statistics"))
        patch_get_default_filter_date = patch(
            PATCH_ACCOUNT.format("_get_default_filter_date"),
            autospec=True,
            return_value=(datetime.now(), datetime.now() + timedelta(days=7)),
        )
        patch_map_chart_statistics = patch(
            PATCH_ACCOUNT.format("_map_chart_statistics")
        )
        fake_client = MagicMock()
        fake_client.get_users_tweets.return_value.data = [
            MagicMock(id="conversation_12345")
        ]
        patch_get_users_tweets = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with (
            patch(
                "odoo.models.BaseModel.search",
                autospec=True,
                side_effect=self.get_search_side_effect_x(),
            ) as mock_search,
            patch_map_chart_statistics as mock_map_chart_statistics,
            patch_super as mock_super,
            patch_get_default_filter_date as mock_get_default_filter_date,
            patch.object(
                type(self.SocialAccount),
                "_get_public_metrics",
                autospec=True,
                return_value=(5, 10, 15, 20, 25),
            ) as mock_get_public_metrics,
            patch_get_users_tweets as mock_get_users_tweets,
        ):
            self.SocialAccount._get_chart_account_statistics(None, None, None)
            self.assertEqual(
                self._count_search_calls(
                    mock_search,
                    model="social.account",
                    domain_leaf=("media_type", "=", "x"),
                ),
                1,
            )
            mock_map_chart_statistics.assert_called_once()
            mock_super.assert_called_once()
            self.assertEqual(
                [
                    call.args[0].media_type
                    for call in mock_get_default_filter_date.call_args_list
                ],
                ["x"],
                msg="Only the x account of this test builds a filter date.",
            )
            mock_get_public_metrics.assert_called_once()
            mock_get_users_tweets.assert_called_once()

    def test_get_chart_account_statistics_skips_other_media(self):
        """An account of another connector gets no x dataset.

        Every connector extends ``social.account``, so the chart of a
        LinkedIn account also runs this override. Without the media type
        guard it queried X for that account and appended its counters.
        """
        sentinel = [{"name": "[OTHER] Account of another media"}]
        with (
            patch(
                PATCH_ACCOUNT.format("_get_chart_account_statistics"),
                return_value=sentinel,
            ),
            patch.object(
                type(self.SocialAccount),
                "_get_users_tweets",
                autospec=True,
            ) as mock_get_users_tweets,
        ):
            res = self.social_account_id._get_chart_account_statistics(
                None, None, "WEEK"
            )
        self.assertEqual(res, sentinel)
        mock_get_users_tweets.assert_not_called()

    @patch(PATCH_REQUEST_POST)
    def test_get_access_token_error_response(self, mock_post):
        self.WizardAccountX.write({"oauth_token": "wiz-token-error"})
        mock_post.return_value = Mock(status_code=403, text="Forbidden")
        with self.assertRaises(UserError):
            self.SocialAccountCredentialX._get_access_token(
                {"oauth_token": "wiz-token-error"}
            )

    @patch(PATCH_REQUEST_POST)
    def test_get_access_token_unexpected_response(self, mock_post):
        self.WizardAccountX.write({"oauth_token": "wiz-token-garbage"})
        mock_post.return_value = Mock(status_code=200, text="garbage-payload")
        with self.assertRaises(UserError):
            self.SocialAccountCredentialX._get_access_token(
                {"oauth_token": "wiz-token-garbage"}
            )

    def test_action_valid_add_account_detects_archived(self):
        self.SocialAccountCredentialX.write({"active": False})
        with self.assertRaises(UserError):
            self.WizardAccountX._action_valid_add_account()

    def test_chart_statistics_rate_limited_uses_persisted(self):
        with (
            patch.object(
                type(self.SocialAccount),
                "_valid_time_request",
                autospec=True,
                return_value=False,
            ),
            patch.object(
                type(self.SocialAccount),
                "_get_users_tweets",
                autospec=True,
            ) as mock_get_users_tweets,
            patch.object(
                type(self.SocialAccount),
                "_map_chart_statistics",
                autospec=True,
                return_value=[],
            ) as mock_map_chart_statistics,
            patch(
                PATCH_ACCOUNT.format("_get_chart_account_statistics"),
                return_value=[],
            ),
        ):
            self.SocialAccountX._get_chart_account_statistics(None, None, "WEEK")
            mock_get_users_tweets.assert_not_called()
            mock_map_chart_statistics.assert_called_once()

    def test_compute_engagement_x_formula(self):
        self.SocialAccountX.write(
            {
                "click_count": 5,
                "like_count": 5,
                "share_count": 0,
                "comment_count": 5,
                "retweet_count": 3,
                "quote_count": 2,
                "impression_count": 400,
            }
        )
        self.assertEqual(self.SocialAccountX.engagement, 5.0)

    def test_compute_engagement_without_impressions(self):
        self.SocialAccountX.write(
            {
                "click_count": 5,
                "impression_count": 0,
            }
        )
        self.assertEqual(self.SocialAccountX.engagement, 0)

    def test_compute_engagement_non_x_account(self):
        account = self.social_account_id
        account.write({"engagement": 7.5})
        account.flush_recordset()
        account.write({"impression_count": 10})
        self.assertEqual(account.engagement, 7.5)
