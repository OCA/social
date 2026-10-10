# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from contextlib import nullcontext
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import requests
from freezegun import freeze_time
from tweepy.errors import BadRequest, Forbidden, Unauthorized

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.social_media_base.exceptions import SocialCredentialsError
from odoo.addons.social_media_base.models.social_account import (
    SocialAccount as SocialAccountBaseCls,
)
from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_MEDIA,
    PATCH_MIXIN_REQUEST,
    PATCH_WIZARD_ACCOUNT,
)

from ..models.social_account import SocialAccount as SocialAccountXCls
from ..social_x_utils import _URL_PRICING_X, _URL_USAGE_CREDITS_X
from ..wizards.wizard_social_account import (
    WizardSocialAccount as WizardSocialAccountXCls,
)
from .test_common_x import (
    PATCH_ACCOUNT_X,
    PATCH_REQUEST_GET,
    PATCH_REQUEST_POST,
    PATCH_WIZARD_ACCOUNT_X,
    TestSocialCommonX,
)

LOGGER_ACCOUNT_X = "odoo.addons.social_media_x.models.social_account"
NOT_PERMITTED_X = "You are not permitted to perform this action."
NOT_ATTACHED_TO_A_PROJECT_X = (
    "When authenticating requests to the X API v2 endpoints, you must use "
    "keys and tokens from a developer App that is attached to a Project. You "
    "can create a project via the developer portal."
)
PREMIUM_HINT_X = "Press Update account to read the plan again"


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
    @patch(PATCH_ACCOUNT_X.format("OAuth1"))
    def test_credentials_when_wizard_matches(self, mock_oauth1, mock_post):
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
        mock_oauth1.return_value = fake_auth
        token, secret = self.SocialAccountCredentialX._get_access_token(kwargs)
        self.assertEqual(token, "tok123")
        self.assertEqual(secret, "sec456")
        mock_oauth1.assert_called_once_with(
            "TEST_KEY", "TEST_SECRET", "wiz-token-123", None
        )
        mock_post.assert_called_once_with(
            "https://api.twitter.com/oauth/access_token",
            auth=fake_auth,
            data={"oauth_verifier": "verif-xyz"},
            timeout=10,
        )

    @patch(PATCH_REQUEST_POST)
    @patch(PATCH_ACCOUNT_X.format("OAuth1"))
    def test_rejects_request_token_without_wizard(self, mock_oauth1, mock_post):
        kwargs = {
            "oauth_token": "no-match-token",
            "oauth_verifier": "verif-abc",
        }
        with self.assertRaises(UserError):
            self.SocialAccountCredentialX._get_access_token(kwargs)
        mock_oauth1.assert_not_called()
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
                "groups_id": [
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
            media_refs = self.SocialAccount._prepare_medias_for_tweet(
                image_ids=[], video_ids=[]
            )
        self.assertEqual(media_refs, {})
        self.assertEqual(captured_calls, [])
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs, {"client_api": False})

    def test_prepare_medias_for_tweet_keys_by_attachment(self):
        """Which attachment produced each ``media_id`` is what is kept."""
        image = self.create_attachment("uploaded_image.jpg")
        video = self.create_attachment("uploaded_video.mp4")
        fake_api = self._fake_api([])
        with patch.object(
            type(self.SocialAccount), "get_client_api", return_value=fake_api
        ):
            media_refs = self.SocialAccount._prepare_medias_for_tweet(
                image_ids=image, video_ids=video
            )
        self.assertEqual(media_refs, {str(image.id): 101, str(video.id): 102})

    def _patch_super(self, record, return_value):
        return self.get_patch_super_x(
            record,
            WizardSocialAccountXCls,
            "_action_valid_add_account",
            return_value=return_value,
        )

    def test_media_type_x_account(self):
        with self._patch_super(
            self.WizardAccountX, return_value="SUPER_OK"
        ) as mock_super:
            with self.assertRaises(UserError):
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
            "action_update_account",
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
            res = self.SocialAccountCredentialX.action_update_account()
        mock_super.assert_called_once_with()
        self.assertIsInstance(res, dict)
        self.assertIn("context", res)
        self.assertTrue(res["context"].get("keep"))
        self.assertEqual(res["context"].get("another"), 1)
        self.assertEqual(res["context"]["default_x_api_key"], "TEST_KEY")
        self.assertEqual(res["context"]["default_x_api_secret"], "TEST_SECRET")

    @patch(PATCH_REQUEST_POST)
    @patch(PATCH_WIZARD_ACCOUNT_X.format("OAuth1"))
    def test_success_returns_act_url_and_sets_token(self, mock_oauth1, mock_post):
        mock_oauth1.return_value = object()
        mock_post.return_value = Mock(
            status_code=200, text="oauth_token=AAA&oauth_token_secret=BBB"
        )
        res = self.WizardAccountX._get_url_authorize()
        mock_oauth1.assert_called_once_with("TEST_KEY", "TEST_SECRET")
        mock_post.assert_called_once_with(
            "https://api.twitter.com/oauth/request_token",
            auth=mock_oauth1.return_value,
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
    @patch(PATCH_WIZARD_ACCOUNT_X.format("OAuth1"))
    def test_bad_response_returns_notification(
        self, mock_oauth1, mock_post, mock_logger
    ):
        mock_oauth1.return_value = object()
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
    @patch(PATCH_WIZARD_ACCOUNT_X.format("OAuth1"))
    def test_app_without_credits_explains_how_to_pay(
        self, mock_oauth1, mock_post, mock_logger
    ):
        mock_oauth1.return_value = object()
        mock_post.return_value = Mock(
            status_code=403,
            text='{"errors":[{"reason":"client-not-enrolled"}]}',
        )
        res = self.WizardAccountX._get_url_authorize()
        params = res.get("params", {})
        self.assertIn("cannot spend against the API", params.get("message", ""))
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
        self.assertIn("cannot spend against the API", message)
        self.assertIn("Pay Per Use project", message)
        self.assertIn("has credit", message)
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

    def test_x_premium_values_without_subscription(self):
        """X answers the text ``"None"``, not a JSON null, without a plan."""
        user = SimpleNamespace(data={"subscription_type": "None"})
        self.assertEqual(
            self.SocialAccount._x_premium_values(user), {"x_premium": False}
        )

    def test_x_premium_values_of_every_plan(self):
        """Every plan of X Premium allows long posts."""
        for plan in ("Basic", "Premium", "PremiumPlus"):
            user = SimpleNamespace(data={"subscription_type": plan})
            self.assertEqual(
                self.SocialAccount._x_premium_values(user),
                {"x_premium": True},
                msg=plan,
            )

    def test_x_premium_values_without_the_field(self):
        """A plan X did not answer leaves the stored one as it was."""
        user = SimpleNamespace(data={"username": "user"})
        self.assertEqual(self.SocialAccount._x_premium_values(user), {})

    def test_x_premium_values_of_a_value_that_is_not_text(self):
        user = SimpleNamespace(data={"subscription_type": None})
        self.assertEqual(self.SocialAccount._x_premium_values(user), {})

    def test_update_account_data(self):
        fake_client = MagicMock()
        fake_data = fake_client.get_me.return_value.data
        fake_data.name = "Account Name X"
        fake_data.username = "account-username-x"
        fake_data.profile_image_url = "https://example.com/img_url"
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.content = b"fake-image-bytes"
        with patch.object(
            type(self.social_account_id),
            "get_client_api",
            autospec=True,
            return_value=fake_client,
        ) as mock_get_client_api, patch(
            PATCH_ACCOUNT_X.format("requests.get"),
            autospec=True,
            return_value=fake_response,
        ) as mock_get, patch.object(
            type(self.social_account_id),
            "write",
            autospec=True,
        ) as mock_write:
            self.social_account_id._update_account_data()
            mock_get_client_api.assert_called_once()
            mock_get.assert_called_once()
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
        with patch.object(
            type(self.social_account_id),
            "get_client_api",
            autospec=True,
            return_value=fake_client,
        ), patch(
            PATCH_ACCOUNT_X.format("requests.get"),
            autospec=True,
            return_value=fake_response,
        ), patch.object(
            type(self.social_account_id),
            "write",
            autospec=True,
        ) as mock_write:
            self.social_account_id._update_account_data()
        mock_write.assert_called_once()
        self.assertEqual(
            mock_write.call_args.args[1],
            {"name": "Account Name X", "username": "account-username-x"},
        )

    def _run_update_account_data(self, raw_data):
        """Update the X account with a user whose raw answer is ``raw_data``.

        :param dict raw_data: the raw answer of X, where the plan travels.
        :return: the client the update asked, to look at what it requested.
        """
        fake_client = MagicMock()
        fake_client.get_me.return_value.data = SimpleNamespace(
            name="Account Name X",
            username="account-username-x",
            profile_image_url="https://example.com/img_url",
            data=raw_data,
        )
        with patch.object(
            type(self.SocialAccountX),
            "get_client_api",
            autospec=True,
            return_value=fake_client,
        ), patch(
            PATCH_ACCOUNT_X.format("requests.get"),
            autospec=True,
            return_value=MagicMock(status_code=404),
        ):
            self.SocialAccountX._update_account_data()
        return fake_client

    def test_update_account_data_asks_the_plan(self):
        fake_client = self._run_update_account_data({"subscription_type": "None"})
        fake_client.get_me.assert_called_once()
        self.assertIn(
            "subscription_type",
            fake_client.get_me.call_args.kwargs["user_fields"],
        )

    def test_update_account_data_reads_a_premium_plan(self):
        self.SocialAccountX.x_premium = False
        self._run_update_account_data({"subscription_type": "Premium"})
        self.assertTrue(self.SocialAccountX.x_premium)

    def test_update_account_data_reads_no_plan(self):
        """An account marked by hand is set right on the next update."""
        self.SocialAccountX.x_premium = True
        self._run_update_account_data({"subscription_type": "None"})
        self.assertFalse(self.SocialAccountX.x_premium)

    def test_update_account_data_without_the_plan_keeps_it(self):
        """X not answering the plan does not leave a Premium account at 280."""
        self.SocialAccountX.x_premium = True
        write = type(self.SocialAccountX).write
        with patch.object(
            type(self.SocialAccountX), "write", autospec=True, side_effect=write
        ) as mock_write:
            self._run_update_account_data({"username": "account-username-x"})
        mock_write.assert_called_once()
        self.assertNotIn("x_premium", mock_write.call_args.args[1])
        self.assertTrue(self.SocialAccountX.x_premium)

    def test_wizard_update_account(self):
        with patch(
            PATCH_WIZARD_ACCOUNT.format("_update_account")
        ) as mock_updt_account_super:
            self.WizardAccount._update_account()
            mock_updt_account_super.assert_called_once()

        with patch.object(
            type(self.WizardAccountX.account_id), "_update_account_data"
        ) as mock_update_account_data, patch(
            PATCH_WIZARD_ACCOUNT.format("_update_account")
        ) as mock_update_account_super:
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

    def _get_wizard_update_x(self, **values):
        """Return an update wizard on the X account, with ``values`` on it."""
        return self.WizardAccount.create(
            dict(
                {"media_id": self.media_x_id.id, "account_id": self.SocialAccountX.id},
                **values,
            )
        )

    @freeze_time("2026-09-30 10:00:00")
    def test_wizard_update_account_stamps_the_last_update(self):
        """Reading the account again is what the form calls its last update."""
        wizard = self._get_wizard_update_x()
        with patch.object(
            type(self.SocialAccountX), "_update_account_data"
        ), self._patch_credit_balance():
            wizard._update_account()
        self.assertEqual(
            self.SocialAccountX.last_update_account, datetime(2026, 9, 30, 10, 0)
        )

    @freeze_time("2026-09-30 10:00:00")
    def test_wizard_update_account_says_it_succeeded(self):
        wizard = self._get_wizard_update_x()
        with patch.object(
            type(self.SocialAccountX), "_update_account_data"
        ), self._patch_credit_balance(), patch.object(
            type(wizard), "_notify_user_client", autospec=True
        ) as mock_notify:
            wizard._update_account()
        mock_notify.assert_called_once()
        kwargs = mock_notify.call_args.kwargs
        self.assertEqual(kwargs["notif_type"], "social_form_success")
        self.assertEqual(
            kwargs["notif_message"], "The account was updated successfully"
        )
        self.assertEqual(kwargs["media"], "x")
        self.assertEqual(kwargs["account_name"], self.SocialAccountX.name)

    @freeze_time("2026-09-30 10:00:00")
    def test_wizard_update_account_not_notify_still_stamps_the_date(self):
        """``not_notify`` silences the notice, not the update it reports."""
        wizard = self._get_wizard_update_x().with_context(not_notify=True)
        with patch.object(
            type(self.SocialAccountX), "_update_account_data"
        ), self._patch_credit_balance(), patch.object(
            type(wizard), "_notify_user_client", autospec=True
        ) as mock_notify:
            wizard._update_account()
        mock_notify.assert_not_called()
        self.assertEqual(
            self.SocialAccountX.last_update_account, datetime(2026, 9, 30, 10, 0)
        )

    def test_wizard_update_credentials_does_not_say_it_succeeded(self):
        """The notice belongs to the association X answers with."""
        fake_url = {"type": "ir.actions.act_url", "url": "https://example.com"}
        for flag in ("update_token", "update_keys"):
            wizard = self._get_wizard_update_x(**{flag: True})
            with patch.object(
                type(wizard), "_get_url_authorize", return_value=fake_url
            ), patch.object(
                type(wizard), "_notify_user_client", autospec=True
            ) as mock_notify:
                wizard._update_account()
            mock_notify.assert_not_called()

    def test_wizard_update_credentials_leaves_the_last_update_to_x(self):
        """Renewing the token or the keys only redirects to X.

        The account is read again when X answers, through the association,
        which is the one that stamps the date.
        """
        fake_url = {"type": "ir.actions.act_url", "url": "https://example.com"}
        for flag in ("update_token", "update_keys"):
            wizard = self._get_wizard_update_x(**{flag: True})
            with patch.object(
                type(wizard), "_get_url_authorize", return_value=fake_url
            ):
                self.assertEqual(wizard._update_account(), fake_url)
            self.assertFalse(self.SocialAccountX.last_update_account, msg=flag)

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

    def test_get_message_many_requests(self):
        self.social_account_id.write({"rate_limit_endpoint": False})
        with patch.object(
            type(self.social_account_id), "_notify_user", autospec=True
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
            type(self.social_account_id), "_notify_user", autospec=True
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
            type(self.social_account_id), "_notify_user", autospec=True
        ) as mocked_notify:
            res = self.social_account_id._get_message_many_requests(
                ex=ex, endpoint="get_users_tweets", view_type="list"
            )
            self.assertFalse(res)
            _, kwargs = mocked_notify.call_args
            self.assertEqual(kwargs["notif_type"], "social_list_info")
            self.assertIn("Get users tweets", kwargs["notif_message"])

    def test_message_many_requests_of_a_callback_goes_through_the_session(self):
        """Associating an account answers with a redirect that outruns the bus.

        The quota of X is the one failure of ``create_account_x`` that did not
        go through ``_notify_failed_association``, so it is the only one whose
        message the redirect could still throw away.
        """
        account = self.social_account_id.with_context(social_media_oauth_callback=True)
        account.write({"rate_limit_endpoint": False})
        ex = _FakeException(
            {
                "x-rate-limit-limit": "50",
                "x-rate-limit-remaining": "0",
                "x-rate-limit-reset": "1735689600",
            }
        )
        mock_request = MagicMock(session={})
        with patch(PATCH_MIXIN_REQUEST, new=mock_request), patch.object(
            type(self.env["bus.bus"]), "_sendone", autospec=True
        ) as mock_sendone:
            self.assertFalse(
                account._get_message_many_requests(ex=ex, endpoint="create_account")
            )
        mock_sendone.assert_not_called()
        kept = mock_request.session["social_media_notification"]
        self.assertEqual(len(kept), 1)
        self.assertIn("Create account", kept[0]["message"])
        self.assertEqual(kept[0]["message_type"], "info")

    def test_action_add_account(self):
        wizard = self.WizardAccountX
        wizard.media_type = "x"
        with patch(
            "odoo.addons.social_media_x.wizards.wizard_social_account."
            "WizardSocialAccount._get_url_authorize",
            autospec=True,
            return_value={"type": "ir.actions.act_url"},
        ) as mock_get_url, patch(
            "odoo.addons.social_media_base.wizards.wizard_social_account."
            "WizardSocialAccount._action_add_account",
            autospec=True,
            return_value={"super": True},
        ) as mock_super:
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
            res = self.social_account_id._valid_time_request(endpoint="get_tweets")
            self.assertFalse(res)
            mock_get_message_many_requests.assert_called_once()

        self.social_account_id.rate_limit_endpoint = False
        res = self.social_account_id._valid_time_request(endpoint="get_tweets")
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
        with patch_get_client_api as mock_get_client_api, patch(
            PATCH_ACCOUNT_X.format("requests.get"),
            autospec=True,
            return_value=fake_response,
        ) as mock_get, patch.object(
            type(self.SocialAccount),
            "_get_access_token_oauth2",
            autospec=True,
            return_value="fake_access_token_oauth2",
        ) as mock_get_access_token_oauth2, patch.object(
            type(self.SocialAccount),
            "_on_account_associated",
            autospec=True,
        ) as mock_on_associated, patch.object(
            type(self.SocialAccount),
            "_x_refresh_credit_balance",
            autospec=True,
        ):
            self.SocialAccount.create_account_x(
                "x_access_token_oauth1", "x_access_secret_oauth1", callback_kwargs
            )
            mock_get_client_api.assert_called_once()
            mock_get.assert_called_once()
            mock_get_access_token_oauth2.assert_called_once()
            mock_on_associated.assert_called_once()
            self.assertTrue(
                mock_on_associated.call_args[0][0],
                msg="The announcement only targets the associated account.",
            )

        patch_get_client_api = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with patch_get_client_api as mock_get_client_api, patch(
            PATCH_ACCOUNT_X.format("requests.get"),
            autospec=True,
            return_value=fake_response,
        ) as mock_get, patch.object(
            type(self.SocialAccount),
            "_get_access_token_oauth2",
            autospec=True,
            return_value=False,
        ) as mock_get_access_token_oauth2, patch.object(
            type(self.SocialAccount),
            "_notify_user_session",
            autospec=True,
            return_value=False,
        ) as mock_notify_user_session:
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
        with patch_get_client_api, patch(
            PATCH_ACCOUNT_X.format("requests.get"),
            autospec=True,
            return_value=fake_response,
        ), patch.object(
            type(self.SocialAccount),
            "_get_access_token_oauth2",
            autospec=True,
            return_value="fake_access_token_oauth2",
        ), patch.object(
            type(self.SocialAccount),
            "_on_account_associated",
            autospec=True,
        ), self._patch_credit_balance():
            self.SocialAccount.create_account_x(
                "x_access_token_oauth1", "x_access_secret_oauth1", callback_kwargs
            )
        accounts = self.SocialAccount.with_context(active_test=False).search(
            [("username", "=", "archived-x-user"), ("media_type", "=", "x")]
        )
        self.assertEqual(len(accounts), 1)
        self.assertTrue(accounts.active)

    def test_create_account_x_works_without_a_sync_module(self):
        """Associating an account only names what ``social_media_base`` declares.

        Linking an account and publishing with it is a valid installation on
        its own, so the association may not reach for a method that arrives
        with a synchronization module.
        """
        self.assertIn(
            "_on_account_associated",
            vars(SocialAccountBaseCls),
            msg="The hook the association announces through is declared by "
            "the base module, so it answers with or without a "
            "synchronization module installed.",
        )

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
        with patch_get_client_api, patch.object(
            type(self.SocialAccount),
            "_notify_user_session",
            autospec=True,
        ) as mock_session, patch.object(
            type(self.SocialAccount),
            "_notify_user_client",
            autospec=True,
        ) as mock_client:
            self.SocialAccount.create_account_x(
                "x_access_token_oauth1", "x_access_secret_oauth1", {}
            )
        mock_session.assert_called_once()
        mock_client.assert_not_called()
        message = mock_session.call_args[0][1]
        self.assertIn("cannot spend against the API", message)
        self.assertIn(_URL_PRICING_X, message)
        self.assertIn("Social Media X", message)

    def _run_create_account_x(
        self,
        username,
        user_id="12345",
        on_associated=None,
        access_token_oauth2="fake_access_token_oauth2",
        get_me_error=None,
        read_credit_balance=False,
        raw_data=None,
        fake_client=None,
    ):
        """Associate ``username`` through the OAuth callback of X.

        X, the avatar download and the OAuth2 token are patched, and so is
        ``_on_account_associated``, which reads the figures of the account.
        The credit balance is stubbed as well, unless the test patches it
        itself to look at the call.

        :param username: user name X answers for the authorized user.
        :param user_id: identifier X answers for the authorized user.
        :param on_associated: side effect of ``_on_account_associated``.
        :param access_token_oauth2: OAuth2 token X answers, if any.
        :param get_me_error: exception X raises when asked for the user.
        :param read_credit_balance: leave the read of the credit balance to
            the caller instead of stubbing it.
        :param dict raw_data: the raw answer of X for the user, where the plan
            travels.
        :param fake_client: the client X is asked through, when the test
            looks at what it requested.
        :return: the X account with that user name, archived or not.
        """
        self.WizardAccountX.write({"oauth_token": "wiz-token-create"})
        fake_client = fake_client or MagicMock()
        fake_client.get_me.side_effect = get_me_error
        data = fake_client.get_me.return_value.data
        data.id = user_id
        data.name = username
        data.username = username
        data.profile_image_url = "https://example.com/img_url"
        if raw_data is not None:
            data.data = raw_data
        with self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        ), patch(
            PATCH_ACCOUNT_X.format("requests.get"),
            autospec=True,
            return_value=MagicMock(status_code=404),
        ), patch.object(
            type(self.SocialAccount),
            "_get_access_token_oauth2",
            autospec=True,
            return_value=access_token_oauth2,
        ), patch.object(
            type(self.SocialAccount),
            "_on_account_associated",
            autospec=True,
            side_effect=on_associated,
        ), nullcontext() if read_credit_balance else self._patch_credit_balance():
            self.SocialAccount.create_account_x(
                "x_access_token_oauth1",
                "x_access_secret_oauth1",
                {"oauth_token": "wiz-token-create"},
            )
        return self.SocialAccount.with_context(active_test=False).search(
            [("username", "=", username), ("media_type", "=", "x")]
        )

    @freeze_time("2026-09-30 10:00:00")
    def test_create_account_x_stamps_the_last_update(self):
        account = self._run_create_account_x("stamped-x-user")
        self.assertEqual(len(account), 1)
        self.assertEqual(account.last_update_account, datetime(2026, 9, 30, 10, 0))

    def test_reassociating_an_account_x_stamps_the_last_update(self):
        """Renewing the token or the keys comes back through the association."""
        existing = self.SocialAccount.create(
            {
                "name": "Reassociated X",
                "username": "reassociated-x-user",
                "remote_ref": "67890",
                "media_id": self.env.ref("social_media_x.social_media_x").id,
                "last_update_account": datetime(2026, 1, 1, 8, 0),
            }
        )
        with freeze_time("2026-09-30 10:00:00"):
            account = self._run_create_account_x("reassociated-x-user", user_id="67890")
        self.assertEqual(account, existing)
        self.assertEqual(account.last_update_account, datetime(2026, 9, 30, 10, 0))

    def test_create_account_x_asks_the_plan(self):
        fake_client = MagicMock()
        self._run_create_account_x("plan-x-user", fake_client=fake_client)
        fake_client.get_me.assert_called_once()
        self.assertIn(
            "subscription_type",
            fake_client.get_me.call_args.kwargs["user_fields"],
        )

    def test_create_account_x_with_a_plan_is_premium(self):
        account = self._run_create_account_x(
            "premium-x-user", raw_data={"subscription_type": "Premium"}
        )
        self.assertEqual(len(account), 1)
        self.assertTrue(account.x_premium)

    def test_reassociating_an_account_x_without_a_plan_is_not_premium(self):
        """An account marked by hand is set right when it is associated again."""
        existing = self.SocialAccount.create(
            {
                "name": "Reassociated X",
                "username": "reassociated-x-user",
                "remote_ref": "67890",
                "media_id": self.env.ref("social_media_x.social_media_x").id,
                "x_premium": True,
            }
        )
        account = self._run_create_account_x(
            "reassociated-x-user",
            user_id="67890",
            raw_data={"subscription_type": "None"},
        )
        self.assertEqual(account, existing)
        self.assertFalse(account.x_premium)

    def _run_create_account_x_in_session(self, username, **kwargs):
        """Associate ``username`` and return the messages kept in the session.

        :param username: user name X answers for the authorized user.
        :param kwargs: the options of :meth:`_run_create_account_x`.
        :return: the notifications the web client shows once reloaded.
        """
        mock_request = MagicMock(session={})
        with patch(PATCH_MIXIN_REQUEST, new=mock_request):
            self._run_create_account_x(username, **kwargs)
        return mock_request.session.get("social_media_notification", [])

    def test_create_account_x_says_it_succeeded(self):
        """The callback reloads the client, so the success waits in the session."""
        with patch.object(
            type(self.SocialAccount),
            "_notify_user_client",
            autospec=True,
        ) as mock_client:
            kept = self._run_create_account_x_in_session("announced-x-user")
        mock_client.assert_not_called()
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["message_type"], "success")
        self.assertIn("The account was associated successfully", kept[0]["message"])
        self.assertIn("X", kept[0]["message"])

    @mute_logger(LOGGER_ACCOUNT_X)
    def test_create_account_x_success_survives_refused_figures(self):
        """X refusing the figures does not hide that the account was linked."""
        kept = self._run_create_account_x_in_session(
            "refused-figures-x-user",
            on_associated=Exception("X refused the figures"),
        )
        self.assertEqual(
            [message["message_type"] for message in kept], ["success", "danger"]
        )
        self.assertIn("The account was associated successfully", kept[0]["message"])
        self.assertIn("X refused the figures", kept[1]["message"])

    @mute_logger(LOGGER_ACCOUNT_X)
    def test_create_account_x_failures_do_not_say_it_succeeded(self):
        failures = {
            "no_oauth2_token": {"access_token_oauth2": False},
            "x_error": {"get_me_error": Exception("X is down")},
        }
        for failure, kwargs in failures.items():
            kept = self._run_create_account_x_in_session(
                f"failed-x-user-{failure}", **kwargs
            )
            self.assertEqual(len(kept), 1, msg=failure)
            self.assertEqual(kept[0]["message_type"], "danger", msg=failure)
            self.assertNotIn("associated successfully", kept[0]["message"], msg=failure)

    @mute_logger(LOGGER_ACCOUNT_X)
    def test_create_account_x_reads_the_credit_balance(self):
        """Read on the new account, even when its figures fail afterwards."""
        with patch.object(
            type(self.SocialAccount), "_x_refresh_credit_balance", autospec=True
        ) as mock_refresh:
            account = self._run_create_account_x(
                "credit-x-user",
                on_associated=Exception("X refused the figures"),
                read_credit_balance=True,
            )
        mock_refresh.assert_called_once()
        self.assertEqual(mock_refresh.call_args.args[0], account)

    def test_create_tweet(self):
        fake_client = MagicMock()
        fake_client.create_tweet.return_value.data = {"id": "tweet_idX"}
        patch_get_client_api = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with patch_get_client_api as mock_get_client_api, patch.object(
            type(self.SocialAccount),
            "_prepare_medias_for_tweet",
            autospec=True,
            return_value={},
        ) as mock_prepare_medias_for_tweet:
            res = self.SocialAccount.create_tweet("Message Test", [], [], None, {})
            self.assertEqual(res, ("tweet_idX", {}))
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
        """The error reaches the caller, which records it on the publication."""
        fake_client = MagicMock()
        fake_client.create_tweet.side_effect = Exception("Error message")
        mock_get_client_api = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with mock_get_client_api, self.assertRaises(Exception) as error:
            self.SocialAccount.create_tweet("Message Test", [], [], None, {})
        self.assertIn("Error message", str(error.exception))

    @mute_logger(LOGGER_ACCOUNT_X)
    def test_create_tweet_refused_authorization(self):
        """X refusing the authorization is told apart from any other error."""
        fake_client = MagicMock()
        fake_client.create_tweet.side_effect = Unauthorized(
            self.generate_magic_mock(status_code=401, json_return_value={})
        )
        mock_get_client_api = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with mock_get_client_api, self.assertRaises(SocialCredentialsError):
            self.SocialAccount.create_tweet("Message Test", [], [], None, {})

    def _create_tweet_refused(self, error, message="Message Test"):
        """Publish ``message`` while X answers ``error``, return what is raised."""
        fake_client = MagicMock()
        fake_client.create_tweet.side_effect = error
        mock_get_client_api = self.get_patch_exceptions_x(
            fake_client=fake_client, valid_time_request=False
        )
        with mock_get_client_api, self.assertRaises(Exception) as raised:
            self.SocialAccountX.create_tweet(message, [], [], None, {})
        return raised.exception

    @mute_logger(LOGGER_ACCOUNT_X)
    def test_create_tweet_refused_post(self):
        """A long post of an account X reported as Premium names the plan.

        The plan is read from X only on association and Update account, so a
        subscription cancelled after that read is only found out here, and the
        user reads how to read it again instead of the raw answer of X.
        """
        self.SocialAccountX.x_premium = True
        error = self._create_tweet_refused(
            self.get_x_refusal(BadRequest, 400, "Invalid Request"), "x" * 329
        )
        self.assertIsInstance(error, UserError)
        self.assertNotIsInstance(error, SocialCredentialsError)
        self.assertIn(PREMIUM_HINT_X, str(error))
        self.assertIn("X Premium", str(error))
        self.assertNotIn("setting", str(error))
        self.assertIn(self.SocialAccountX.display_name, str(error))

    @mute_logger(LOGGER_ACCOUNT_X)
    def test_create_tweet_refused_post_without_premium(self):
        """A refused post of an account without X Premium keeps the text of X."""
        error = self._create_tweet_refused(
            self.get_x_refusal(BadRequest, 400, "Invalid Request"), "x" * 329
        )
        self.assertIsInstance(error, UserError)
        self.assertNotIn(PREMIUM_HINT_X, str(error))
        self.assertIn("Invalid Request", str(error))

    @mute_logger(LOGGER_ACCOUNT_X)
    def test_create_tweet_forbidden_is_not_a_credentials_error(self):
        """A 403 is a post X refuses, not a token it no longer accepts."""
        error = self._create_tweet_refused(
            self.get_x_refusal(Forbidden, 403, NOT_PERMITTED_X), "x" * 100
        )
        self.assertIsInstance(error, UserError)
        self.assertNotIsInstance(error, SocialCredentialsError)
        self.assertNotIn(PREMIUM_HINT_X, str(error))
        self.assertIn(NOT_PERMITTED_X, str(error))

    @mute_logger(LOGGER_ACCOUNT_X)
    def test_create_tweet_forbidden_long_post_of_a_premium_account(self):
        """The 403 X answers a long post of a Premium account names the plan."""
        self.SocialAccountX.x_premium = True
        error = self._create_tweet_refused(
            self.get_x_refusal(Forbidden, 403, NOT_PERMITTED_X), "x" * 329
        )
        self.assertIsInstance(error, UserError)
        self.assertNotIsInstance(error, SocialCredentialsError)
        self.assertIn(PREMIUM_HINT_X, str(error))

    @mute_logger(LOGGER_ACCOUNT_X)
    def test_create_tweet_forbidden_app_without_paid_plan(self):
        """An App that cannot spend is explained with the pricing address."""
        error = self._create_tweet_refused(
            self.get_x_refusal(Forbidden, 403, NOT_ATTACHED_TO_A_PROJECT_X)
        )
        self.assertIsInstance(error, UserError)
        self.assertNotIsInstance(error, SocialCredentialsError)
        self.assertIn("cannot spend against the API", str(error))
        self.assertIn(_URL_PRICING_X, str(error))

    def test_refused_post_of_an_app_without_paid_plan(self):
        """The App that cannot spend is explained, with the pricing address.

        The message ends on the failed publication, stored as plain text, so
        the address is written as it is and not as an anchor.
        """
        error = self.get_x_refusal(Forbidden, 403, NOT_ATTACHED_TO_A_PROJECT_X)
        message = self.SocialAccountX._x_refused_post_message(error, "Message Test")
        self.assertIn("cannot spend against the API", message)
        self.assertIn(_URL_PRICING_X, message)
        self.assertNotIn("<a ", message)
        self.assertNotIn(PREMIUM_HINT_X, message)

    def test_refused_long_post_of_a_premium_account_is_forbidden(self):
        """A 403 for a long post of an account read as Premium names the plan."""
        self.SocialAccountX.x_premium = True
        error = self.get_x_refusal(Forbidden, 403, NOT_PERMITTED_X)
        message = self.SocialAccountX._x_refused_post_message(error, "x" * 329)
        self.assertIn(PREMIUM_HINT_X, message)
        self.assertIn(self.SocialAccountX.display_name, message)
        self.assertIn(NOT_PERMITTED_X, message)

    def test_refused_long_post_of_a_premium_account_is_bad_request(self):
        """A 400 for a long post of an account read as Premium names the plan."""
        self.SocialAccountX.x_premium = True
        error = self.get_x_refusal(BadRequest, 400, "Invalid Request")
        message = self.SocialAccountX._x_refused_post_message(error, "x" * 329)
        self.assertIn(PREMIUM_HINT_X, message)

    def test_refused_post_without_premium_keeps_the_text_of_x(self):
        """Without X Premium the plan has nothing to do with the refusal."""
        for error_class, status_code in ((Forbidden, 403), (BadRequest, 400)):
            error = self.get_x_refusal(error_class, status_code, NOT_PERMITTED_X)
            message = self.SocialAccountX._x_refused_post_message(error, "x" * 329)
            self.assertNotIn(PREMIUM_HINT_X, message)
            self.assertIn(self.SocialAccountX.display_name, message)
            self.assertIn(NOT_PERMITTED_X, message)

    def test_refused_post_does_not_repeat_the_full_stop_of_x(self):
        """The text of X ends in a full stop, and the message closes it once."""
        self.SocialAccountX.x_premium = True
        error = self.get_x_refusal(Forbidden, 403, NOT_PERMITTED_X)
        for message in ("x" * 329, "x" * 100):
            reason = self.SocialAccountX._x_refused_post_message(error, message)
            self.assertNotIn("..", reason)
            self.assertIn("You are not permitted to perform this action.", reason)

    def test_refused_short_post_of_a_premium_account_keeps_the_text_of_x(self):
        """A post within the limit of any plan was not refused for its length."""
        self.SocialAccountX.x_premium = True
        error = self.get_x_refusal(Forbidden, 403, NOT_PERMITTED_X)
        message = self.SocialAccountX._x_refused_post_message(error, "x" * 100)
        self.assertNotIn(PREMIUM_HINT_X, message)
        self.assertIn(NOT_PERMITTED_X, message)

    def test_refresh_credentials_is_not_possible_on_x(self):
        """X gives no way to renew the token from Odoo."""
        self.assertFalse(self.SocialAccountX._refresh_credentials())

    def _patch_credit_balance(self):
        """Stub the credit balance, which has tests of its own."""
        return patch.object(
            type(self.SocialAccount), "_x_refresh_credit_balance", autospec=True
        )

    def _patch_x_check_updates(self, return_value=False):
        return patch.object(
            type(self.SocialAccount),
            "_x_check_updates",
            autospec=True,
            return_value=return_value,
        )

    def _patch_check_domain(self, domain):
        return patch.object(
            type(self.SocialAccount),
            "_get_check_media_updates_domain",
            autospec=True,
            return_value=domain,
        )

    def test_run_check_media_updates_asks_base_which_accounts_to_walk(self):
        """The domain is the one base answers, never an empty one.

        A module that reads the social media has reasons to leave an account
        out —the one whose first import has not run yet—, and writing the
        domain here instead of asking would skip them.
        """
        with self._patch_check_domain(
            [("id", "=", self.SocialAccountX.id)]
        ) as mock_domain, self._patch_x_check_updates() as mock_check, (
            self._patch_credit_balance()
        ):
            self.SocialAccount._run_check_media_updates()
        mock_domain.assert_called()
        self.assertEqual(
            mock_check.call_args.args[0],
            self.SocialAccountX,
            msg="The accounts left out by the domain never reach the hook.",
        )

    def test_run_check_media_updates_hands_over_the_x_accounts(self):
        """The X accounts base allows are announced once, in one recordset.

        The domain is narrowed to the accounts of this test because the same
        pass walks the accounts of every other connector installed, and each
        of them asks its own social media.
        """
        accounts_x = self.SocialAccountX + self.SocialAccountCredentialX
        with self._patch_check_domain(
            [("id", "in", accounts_x.ids)]
        ), self._patch_x_check_updates() as mock_check, self._patch_credit_balance():
            self.SocialAccount._run_check_media_updates()
        mock_check.assert_called_once()
        self.assertEqual(mock_check.call_args.args[0], accounts_x)

    def test_run_check_media_updates_leaves_the_other_media_alone(self):
        """An account of another media never reaches the hook of X."""
        with self._patch_check_domain(
            [("id", "=", self.social_account_id.id)]
        ), self._patch_x_check_updates() as mock_check:
            self.assertFalse(self.SocialAccount._run_check_media_updates())
        mock_check.assert_not_called()

    def test_x_check_updates_asks_nothing_to_x(self):
        """The hook is empty here: reading a timeline back is sync's business.

        The implementation of this module is called directly, because a
        synchronization module installed on top answers the very same call
        through the registry class, and what is fixed here is what the
        connector does on its own.
        """
        with patch.object(
            type(self.SocialAccount), "get_client_api", autospec=True
        ) as mock_client:
            self.assertFalse(SocialAccountXCls._x_check_updates(self.SocialAccountX))
        mock_client.assert_not_called()

    def test_run_check_media_updates_asks_nothing_to_x(self):
        """The pass answers a bool and spends no request of the plan.

        The connector has nothing to check on X: its token does not expire and
        the API reports no figures by day. The hook is stubbed because a
        synchronization module installed on top answers it with an import,
        and what is fixed here is the cost of the pass on its own. So is the
        credit balance, a single request per API Key with tests of its own.
        """
        with self._patch_x_check_updates(), self._patch_credit_balance(), patch.object(
            type(self.SocialAccount), "get_client_api", autospec=True
        ) as mock_client:
            result = self.SocialAccount._run_check_media_updates()
        self.assertIsInstance(result, bool)
        mock_client.assert_not_called()

    def test_run_check_media_updates_keeps_the_chain(self):
        """A connector does not decide for the ones checked before it.

        The loop of base is the only place where a refused credential is
        flagged, for every connector, so its answer is kept and OR-ed.
        """
        patch_super = self.get_patch_super_x(
            self.SocialAccountX,
            SocialAccountXCls,
            "_run_check_media_updates",
            autospec=True,
            return_value=True,
        )
        with patch_super as mock_super, self._patch_x_check_updates(), (
            self._patch_credit_balance()
        ):
            self.assertTrue(self.SocialAccount._run_check_media_updates())
        mock_super.assert_called_once()

    def test_update_account(self):
        def super_action():
            return {
                "type": "ir.actions.act_window",
                "context": {"from_super": True},
            }

        with self._patch_super_update(
            self.SocialAccountX, super_action()
        ) as mock_update_account_super:
            res = self.SocialAccountX.action_update_account()
        mock_update_account_super.assert_called_once()
        self.assertTrue(res["context"]["from_super"])
        self.assertFalse(res["context"]["default_x_api_key"])
        self.assertFalse(res["context"]["default_x_api_secret"])

        with self._patch_super_update(
            self.SocialAccount, super_action()
        ) as mock_update_account_super:
            res_empty = self.SocialAccount.action_update_account()
        mock_update_account_super.assert_called_once()
        self.assertEqual(res_empty["context"], {"from_super": True})

    def test_the_engagement_counts_the_retweets_and_the_quotes(self):
        """The rate is the generic one; what X widens is its numerator.

        Twenty interactions in four hundred impressions, five of them the
        retweets and the quotes X counts and nobody else does. The unit is the
        ratio of the whole family, so it reads 0,05 and not 5.
        """
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
        self.assertEqual(self.SocialAccountX.interactions_count, 20)
        self.assertEqual(self.SocialAccountX.engagement, 0.05)

    def test_the_engagement_without_impressions_is_zero(self):
        self.SocialAccountX.write(
            {
                "click_count": 5,
                "impression_count": 0,
            }
        )
        self.assertEqual(self.SocialAccountX.engagement, 0)

    def test_a_written_engagement_does_not_survive_a_counter(self):
        """X declares no field of its own, so no inverse freezes the value."""
        self.SocialAccountX.write({"like_count": 20, "impression_count": 400})
        self.SocialAccountX.write({"engagement": 7.5})
        self.SocialAccountX.write({"impression_count": 200})
        self.assertEqual(self.SocialAccountX.engagement, 0.1)

    def test_the_engagement_survives_refreshing_the_card(self):
        """The case that used to answer zero: X has no daily series.

        The card falls back to the counters of the publications, which is
        where the connector stores what X reports, and the rate comes out of
        the totals instead of the average of a field nobody fills in.
        """
        self.SocialAccountX.post_account_ids.write(
            {"like_count": 0, "impression_count": 0}
        )
        self.SocialPostAccountX.write({"like_count": 40, "impression_count": 1000})
        self.SocialAccountX._refresh_account_statistics()
        self.assertEqual(self.SocialAccountX.impression_count, 1000)
        self.assertEqual(self.SocialAccountX.engagement, 0.04)

    def test_interaction_count_fields_adds_the_retweets_and_the_quotes(self):
        """The hook is what feeds both the sum and its dependency."""
        self.assertEqual(
            self.SocialAccountX._interaction_count_fields(),
            [
                "click_count",
                "like_count",
                "share_count",
                "comment_count",
                "retweet_count",
                "quote_count",
            ],
        )
        self.SocialAccountX.write(
            {
                "click_count": 1,
                "like_count": 2,
                "share_count": 3,
                "comment_count": 4,
                "retweet_count": 5,
                "quote_count": 6,
            }
        )
        self.assertEqual(self.SocialAccountX.interactions_count, 21)


class TestSocialAccountCreditX(TestSocialCommonX):
    """The credit balance of the developer App, read from ``/2/usage/credits``."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        values = {
            "media_id": cls.media_x_id.id,
            "x_credit_balance": 3.0,
            "x_credit_balance_date": datetime(2026, 9, 1),
        }
        cls.account_a1 = cls.SocialAccount.create(
            {
                **values,
                "name": "A1",
                "x_api_key": "KEY_A",
                "x_access_token_oauth2": "BEARER_A1",
            }
        )
        cls.account_a2 = cls.SocialAccount.create(
            {
                **values,
                "name": "A2",
                "x_api_key": "KEY_A",
                "x_access_token_oauth2": "BEARER_A2",
            }
        )
        cls.account_b = cls.SocialAccount.create(
            {
                **values,
                "name": "B",
                "x_api_key": "KEY_B",
                "x_access_token_oauth2": "BEARER_B",
            }
        )
        cls.accounts_credit = cls.account_a1 + cls.account_a2 + cls.account_b
        cls.user_a1, cls.user_a2 = (
            mail_new_test_user(
                cls.env,
                login=login,
                groups="base.group_user,social_media_base.group_social_media_user",
            )
            for login in ("credit_user_a1", "credit_user_a2")
        )
        cls.account_a1.user_id = cls.user_a1
        cls.account_a2.user_id = cls.user_a2

    def _credits_response(self, total=4.68, prepaid=None, status_code=200):
        """Build the answer of X to ``GET /2/usage/credits``."""
        response = self.generate_magic_mock(
            status_code=status_code,
            json_return_value={
                "data": {
                    "free_balance": 0.0,
                    "free_grants": [],
                    "prepaid_balance": total if prepaid is None else prepaid,
                    "total_balance": total,
                }
            },
        )
        response.headers = {}
        response.text = "answer of X"
        return response

    def _patch_credits(self, **answer_by_bearer):
        """Patch the call, answering by the bearer token it carries."""

        def get(url, headers=None, timeout=None):
            answer = answer_by_bearer[headers["Authorization"].split()[-1]]
            if isinstance(answer, Exception):
                raise answer
            return answer

        return patch(PATCH_REQUEST_GET, side_effect=get)

    def _assert_balance(self, accounts, balance, date):
        for account in accounts:
            self.assertEqual(account.x_credit_balance, balance, msg=account.name)
            self.assertEqual(account.x_credit_balance_date, date, msg=account.name)

    @freeze_time("2026-09-30 23:37:00")
    def test_credit_balance_is_written_with_its_date(self):
        with self._patch_credits(BEARER_B=self._credits_response(4.68)) as mock_get:
            self.account_b._x_refresh_credit_balance()
        mock_get.assert_called_once_with(
            _URL_USAGE_CREDITS_X,
            headers={"Authorization": "Bearer BEARER_B"},
            timeout=10,
        )
        self._assert_balance(self.account_b, 4.68, datetime(2026, 9, 30, 23, 37))

    @freeze_time("2026-09-30 23:37:00")
    def test_credit_balance_is_asked_once_per_api_key(self):
        """The balance is the one of the App, so an API Key is one call."""
        with self._patch_credits(
            BEARER_A1=self._credits_response(4.68),
            BEARER_B=self._credits_response(12.5),
        ) as mock_get:
            self.accounts_credit._x_refresh_credit_balance()
        self.assertEqual(mock_get.call_count, 2)
        read_on = datetime(2026, 9, 30, 23, 37)
        self._assert_balance(self.account_a1 + self.account_a2, 4.68, read_on)
        self._assert_balance(self.account_b, 12.5, read_on)

    def test_credit_balance_of_a_negative_prepaid_is_zero(self):
        """X compares ``total_balance``, never negative, to block the calls."""
        with self._patch_credits(BEARER_B=self._credits_response(0.0, prepaid=-0.4)):
            self.account_b._x_refresh_credit_balance()
        self.assertEqual(self.account_b.x_credit_balance, 0.0)
        self.assertNotEqual(self.account_b.x_credit_balance_date, datetime(2026, 9, 1))

    def test_credit_balance_rate_limit_waits_for_the_window(self):
        """A ``429`` keeps the window on the API Key and the balance as it was."""
        response = self._credits_response(status_code=429)
        response.headers = {
            "x-rate-limit-limit": "30",
            "x-rate-limit-remaining": "0",
            "x-rate-limit-reset": "9999999999",
        }
        accounts_a = self.account_a1 + self.account_a2
        with self._patch_credits(BEARER_A1=response) as mock_get, patch.object(
            type(self.env["bus.bus"]), "_sendone", autospec=True
        ) as mock_sendone:
            accounts_a._x_refresh_credit_balance()
            self.account_a2._x_refresh_credit_balance()
        mock_get.assert_called_once()
        mock_sendone.assert_not_called()
        for account in accounts_a:
            self.assertEqual(
                account.rate_limit_endpoint["usage_credits"]["x-rate-limit-reset"],
                9999999999,
            )
        self._assert_balance(accounts_a, 3.0, datetime(2026, 9, 1))

    def test_credit_balance_errors_leave_it_as_it_was(self):
        """A failure is logged only, and the other API Keys are still written."""
        failures = {
            "401": self._credits_response(status_code=401),
            "403": self._credits_response(status_code=403),
            "500": self._credits_response(status_code=500),
            "network": requests.ConnectionError("unreachable"),
            "format": self.generate_magic_mock(
                status_code=200, json_return_value={"errors": []}
            ),
        }
        for name, failure in failures.items():
            with self.subTest(failure=name), self._patch_credits(
                BEARER_A1=failure, BEARER_B=self._credits_response(4.68)
            ), patch.object(
                type(self.env["bus.bus"]), "_sendone", autospec=True
            ) as mock_sendone, self.assertLogs(LOGGER_ACCOUNT_X, level="WARNING"):
                self.accounts_credit._x_refresh_credit_balance()
            mock_sendone.assert_not_called()
            self._assert_balance(
                self.account_a1 + self.account_a2, 3.0, datetime(2026, 9, 1)
            )
            self.assertFalse(
                any((self.account_a1 + self.account_a2).mapped("need_update"))
            )
            self.assertEqual(self.account_b.x_credit_balance, 4.68)

    def _read_balance(self, accounts, total):
        """Read ``total`` as the balance of ``accounts``, one API Key.

        :return: the mock of the notification on the bus.
        """
        bearer = accounts[0].sudo().x_access_token_oauth2
        with self._patch_credits(
            **{bearer: self._credits_response(total)}
        ), patch.object(
            type(self.SocialAccount), "_notify_user_client", autospec=True
        ) as mock_notify:
            accounts._x_refresh_credit_balance()
        return mock_notify

    def _credit_notes(self, account):
        return account.message_ids.filtered(
            lambda message: "credit balance" in (message.body or "")
        )

    def test_credit_warning_is_given_once_per_drop(self):
        """Under the threshold warns once, until the balance is over it again."""
        mock_notify = self._read_balance(self.account_b, 0.8)
        mock_notify.assert_called_once()
        self.assertEqual(
            mock_notify.call_args.kwargs["target"], self.account_b.user_id.partner_id
        )
        self.assertEqual(mock_notify.call_args.kwargs["notif_type"], "social_form_info")
        self.assertIn("USD 0.80", mock_notify.call_args.kwargs["notif_message"])
        self.assertIn("USD 1.00", mock_notify.call_args.kwargs["notif_message"])
        note = self._credit_notes(self.account_b)
        self.assertEqual(len(note), 1)
        self.assertIn(self.account_b.user_id.partner_id, note.partner_ids)

        self._read_balance(self.account_b, 0.6).assert_not_called()
        self.assertEqual(len(self._credit_notes(self.account_b)), 1)

        self._read_balance(self.account_b, 2.0).assert_not_called()
        self.assertFalse(self.account_b.x_credit_warned)

        self._read_balance(self.account_b, 0.5).assert_called_once()
        self.assertEqual(len(self._credit_notes(self.account_b)), 2)

    def test_credit_warning_of_a_used_up_balance(self):
        mock_notify = self._read_balance(self.account_b, 0.0)
        mock_notify.assert_called_once()
        self.assertEqual(
            mock_notify.call_args.kwargs["notif_type"], "social_form_danger"
        )
        self.assertIn("used up", mock_notify.call_args.kwargs["notif_message"])
        self.assertIn("used up", self._credit_notes(self.account_b).body)

        self._read_balance(self.account_b, 0.0).assert_not_called()
        self.assertEqual(len(self._credit_notes(self.account_b)), 1)

    def test_credit_warning_travels_on_a_type_the_client_listens_to(self):
        """The web client only subscribes to the form types of the bus."""
        for total, message_type in ((0.5, "info"), (0.0, "danger")):
            with self.subTest(total=total), patch.object(
                type(self.env["bus.bus"]), "_sendone", autospec=True
            ) as mock_sendone:
                self._read_balance_on_the_bus(self.account_b, total)
            mock_sendone.assert_called_once()
            _bus, _target, bus_type, payload = mock_sendone.call_args.args
            self.assertEqual(bus_type, "social_form_info")
            self.assertEqual(payload["message_type"], message_type)

    def _read_balance_on_the_bus(self, accounts, total):
        bearer = accounts[0].sudo().x_access_token_oauth2
        with self._patch_credits(**{bearer: self._credits_response(total)}):
            accounts._x_refresh_credit_balance()

    def test_credit_warning_of_a_low_balance_then_used_up(self):
        self._read_balance(self.account_b, 0.5)
        mock_notify = self._read_balance(self.account_b, 0.0)
        self.assertEqual(
            mock_notify.call_args.kwargs["notif_type"], "social_form_danger"
        )
        self.assertEqual(len(self._credit_notes(self.account_b)), 2)

    def test_credit_warning_at_zero_warns_only_when_used_up(self):
        self.account_b.x_credit_warning = 0.0
        self._read_balance(self.account_b, 0.3).assert_not_called()
        self._read_balance(self.account_b, 0.0).assert_called_once()

    def test_credit_warning_on_the_first_read(self):
        """A balance never read counts as over the threshold."""
        self.account_b.write({"x_credit_balance": 0.0, "x_credit_balance_date": False})
        self._read_balance(self.account_b, 0.5).assert_called_once()

    def test_credit_warning_on_the_first_read_of_a_used_up_balance(self):
        self.account_b.write({"x_credit_balance": 0.0, "x_credit_balance_date": False})
        mock_notify = self._read_balance(self.account_b, 0.0)
        self.assertEqual(
            mock_notify.call_args.kwargs["notif_type"], "social_form_danger"
        )

    def test_credit_warning_of_a_raised_threshold(self):
        """Raising the threshold over the balance warns on the next read."""
        self._read_balance(self.account_b, 4.68).assert_not_called()
        self.account_b.x_credit_warning = 10.0
        self._read_balance(self.account_b, 4.68).assert_called_once()
        self._read_balance(self.account_b, 4.68).assert_not_called()

    def test_credit_warning_reaches_every_responsible(self):
        """An API Key shared by two accounts warns the responsible of each."""
        mock_notify = self._read_balance(self.account_a1 + self.account_a2, 0.5)
        self.assertEqual(
            {call.kwargs["target"] for call in mock_notify.call_args_list},
            {self.user_a1.partner_id, self.user_a2.partner_id},
        )
        for account, user in (
            (self.account_a1, self.user_a1),
            (self.account_a2, self.user_a2),
        ):
            self.assertIn(user.partner_id, self._credit_notes(account).partner_ids)

    def test_credit_warning_of_the_callback_waits_in_the_session(self):
        """The redirect of the OAuth callback would outrun the bus."""
        self.account_b.user_id = self.env.user
        mock_request = MagicMock(session={})
        with patch(PATCH_MIXIN_REQUEST, new=mock_request):
            mock_notify = self._read_balance(
                self.account_b.with_context(social_media_oauth_callback=True), 0.5
            )
        mock_notify.assert_not_called()
        kept = mock_request.session.get("social_media_notification", [])
        self.assertEqual([message["message_type"] for message in kept], ["info"])
        self.assertIn("USD 0.50", kept[0]["message"])
        self.assertEqual(len(self._credit_notes(self.account_b)), 1)

    def test_credit_warning_of_the_callback_reaches_the_others_on_the_bus(self):
        """Only the user reloading the client reads the session."""
        mock_request = MagicMock(session={})
        accounts = (self.account_a1 + self.account_a2).with_context(
            social_media_oauth_callback=True
        )
        with patch(PATCH_MIXIN_REQUEST, new=mock_request):
            mock_notify = self._read_balance(accounts, 0.5)
        self.assertFalse(mock_request.session.get("social_media_notification"))
        self.assertEqual(
            {call.kwargs["target"] for call in mock_notify.call_args_list},
            {self.user_a1.partner_id, self.user_a2.partner_id},
        )

    def _patch_refresh_credit_balance(self):
        return patch.object(
            type(self.SocialAccount), "_x_refresh_credit_balance", autospec=True
        )

    def test_credit_balance_is_read_by_the_cron_on_its_domain(self):
        """The cron reads the accounts base allows, all of them in one call."""
        with patch.object(
            type(self.SocialAccount),
            "_get_check_media_updates_domain",
            autospec=True,
            return_value=[("id", "in", (self.account_a1 + self.account_b).ids)],
        ), patch.object(
            type(self.SocialAccount), "_x_check_updates", autospec=True
        ), self._patch_refresh_credit_balance() as mock_refresh:
            self.SocialAccount._run_check_media_updates()
        mock_refresh.assert_called_once()
        self.assertEqual(
            mock_refresh.call_args.args[0], self.account_a1 + self.account_b
        )

    def test_credit_balance_is_read_by_update_account(self):
        wizard = self.WizardAccount.create(
            {"media_id": self.media_x_id.id, "account_id": self.account_b.id}
        )
        with patch.object(
            type(self.account_b), "_update_account_data"
        ), self._patch_refresh_credit_balance() as mock_refresh:
            wizard._update_account()
        mock_refresh.assert_called_once()
        self.assertEqual(mock_refresh.call_args.args[0], self.account_b)

    def test_credit_balance_is_not_read_when_the_keys_are_updated(self):
        """Updating keys or token goes through X first; nothing is read yet."""
        wizard = self.WizardAccount.create(
            {
                "media_id": self.media_x_id.id,
                "account_id": self.account_b.id,
                "update_keys": True,
            }
        )
        with patch.object(
            type(wizard), "_get_url_authorize", return_value={}
        ), self._patch_refresh_credit_balance() as mock_refresh:
            wizard._update_account()
        mock_refresh.assert_not_called()

    def test_credit_balance_is_read_by_refresh_statistics(self):
        for account, calls in ((self.account_b, 1), (self.social_account_id, 0)):
            with self.subTest(account=account.name), self.get_patch_super_x(
                account, SocialAccountXCls, "action_refresh_statistics", autospec=True
            ) as mock_super, self._patch_refresh_credit_balance() as mock_refresh:
                account.action_refresh_statistics()
            mock_super.assert_called_once()
            self.assertEqual(mock_refresh.call_count, calls)

    def test_credit_balance_of_another_media_is_never_asked(self):
        with patch(PATCH_REQUEST_GET) as mock_get:
            self.social_account_id._x_refresh_credit_balance()
        mock_get.assert_not_called()


class TestSocialMediaX(TestSocialCommonX):
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
