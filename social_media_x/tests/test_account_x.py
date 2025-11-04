# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from odoo.exceptions import ValidationError

from odoo.addons.social_media_base.tests.test_social_common import (
    PATCH_SOCIAL_BASE_MIXIN,
)

from .test_common_x import (
    PATCH_ACCOUNT_X,
    PATCH_REQUEST_POST,
    PATCH_WIZARD_ACCOUNT,
    TestSocialCommonX,
)


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
        kwargs = {
            "oauth_token": "wiz-token-123",
            "oauth_verifier": "verif-xyz",
        }
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
    def test_falls_back_to_model_credentials_when_no_wizard(
        self, mock_get_oauth, mock_post
    ):
        kwargs = {
            "oauth_token": "no-match-token",
            "oauth_verifier": "verif-abc",
        }
        mock_post.return_value.text = "oauth_token=A&oauth_token_secret=B"
        fake_auth = object()
        mock_get_oauth.return_value = fake_auth
        token, secret = self.SocialAccountCredentialX._get_access_token(kwargs)
        self.assertEqual(token, "A")
        self.assertEqual(secret, "B")
        mock_get_oauth.assert_called_once_with(
            "TEST_KEY", "TEST_SECRET", request_access_token=kwargs
        )
        mock_post.assert_called_once_with(
            "https://api.twitter.com/oauth/access_token",
            auth=fake_auth,
            data={"oauth_verifier": "verif-abc"},
            timeout=10,
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
            access_token_secret=False,  # idem
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
                # Guardamos lo que recibe para asserts
                data = file.read()
                self.cap.append((filename, data))
                self.counter += 1
                return type("FakeMedia", (), {"media_id": 100 + self.counter})

        return _FakeAPI(captured)

    def test_image_datas_when_provided(self):
        raw = b"hello-world"
        b64 = base64.b64encode(raw).decode()
        image_datas = f"data:image/jpeg;base64,{b64}"
        captured_calls = []
        fake_api = self._fake_api(captured_calls)
        with patch.object(
            type(self.SocialAccount), "get_client_api", return_value=fake_api
        ) as mock_get:
            media_ids = self.SocialAccount._prepare_medias_for_tweet(
                image_datas=image_datas
            )
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs, {"client_api": False})
        self.assertEqual(media_ids, [101])
        self.assertEqual(len(captured_calls), 1)
        filename, data = captured_calls[0]
        self.assertEqual(filename, "imagen.jpg")
        self.assertEqual(data, raw)

    def test_handles_empty_list(self):
        captured_calls = []
        fake_api = self._fake_api(captured_calls)
        with patch.object(
            type(self.SocialAccount), "get_client_api", return_value=fake_api
        ) as mock_get:
            media_ids = self.SocialAccount._prepare_medias_for_tweet(image_ids=[])
        self.assertEqual(media_ids, [])
        self.assertEqual(captured_calls, [])
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs, {"client_api": False})

    def test_create_tweet_with_medias(self):
        with (
            patch.object(type(self.SocialAccount), "get_client_api") as mock_get_api,
            patch.object(
                type(self.SocialAccount), "_prepare_medias_for_tweet"
            ) as mock_prep,
        ):
            fake_client = Mock()
            fake_client.create_tweet.return_value = type(
                "Response", (), {"data": {"id": "123"}}
            )()
            mock_get_api.return_value = fake_client
            mock_prep.return_value = [101, 102]
            image_ids = ["dummy"]
            tweet_id = self.SocialAccount.create_tweet("Message test", image_ids)
            self.assertEqual(tweet_id, "123")
            mock_get_api.assert_called_once_with()
            mock_prep.assert_called_once_with(image_ids)
            fake_client.create_tweet.assert_called_once_with(
                text="Message test",
                media_ids=[101, 102],
            )

    @patch(PATCH_SOCIAL_BASE_MIXIN.format("_notify_user_client"))
    def test_create_tweet_without_medias(self, mock_notify):
        with (
            patch.object(type(self.SocialAccount), "get_client_api") as mock_get_api,
            patch.object(
                type(self.SocialAccount), "_prepare_medias_for_tweet", return_value=[]
            ) as mock_prep,
        ):
            fake_client = Mock()
            fake_client.create_tweet.return_value = type(
                "Response", (), {"data": {"id": "456"}}
            )()
            mock_get_api.return_value = fake_client
            tweet_id = self.SocialAccount.create_tweet("Without images", image_ids=[])
            self.assertEqual(tweet_id, "456")
            mock_get_api.assert_called_once_with()
            mock_prep.assert_called_once_with([])
            fake_client.create_tweet.assert_called_once_with(
                text="Without images",
                media_ids=None,
            )
            mock_notify.assert_not_called()

    def _patch_super(self, record, return_value):
        SocialAccount = record.__class__
        ParentSocialAccount = SocialAccount.__mro__[1]
        return patch.object(
            ParentSocialAccount, "_action_valid_add_account", return_value=return_value
        )

    def test_media_type_x_account(self):
        with self._patch_super(
            self.WizardAccountX, return_value="SUPER_OK"
        ) as mock_super:
            res = self.WizardAccountX._action_valid_add_account()
        mock_super.assert_called_once_with()
        self.assertEqual(res, "SUPER_OK")

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
        SocialClass = record.__class__
        ParentSocialClass = SocialClass.__mro__[1]
        return patch.object(
            ParentSocialClass, "update_account", return_value=return_action
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
        with self._patch_super_update(self.SocialAccount, super_action) as mock_super:
            res = self.SocialAccount.update_account()
        mock_super.assert_called_once_with()
        self.assertIsInstance(res, dict)
        self.assertIn("context", res)
        self.assertTrue(res["context"].get("keep"))
        self.assertEqual(res["context"].get("another"), 1)
        self.assertEqual(res["context"]["default_x_api_key"], "DEF_TEST_KEY")
        self.assertEqual(res["context"]["default_x_api_secret"], "DEF_TEST_SECRET")

    def _patch_super_action_add_account(self, record, return_value):
        SocialClass = record.__class__
        ParentSocialClass = SocialClass.__mro__[1]
        return patch.object(
            ParentSocialClass, "_action_add_account", return_value=return_value
        )

    def test_action_add_account(self):
        with (
            self._patch_super_action_add_account(
                self.WizardAccountX,
                return_value={
                    "type": "ir.actions.act_url",
                    "url": "https://auth.example",
                },
            ) as mock_super,
            patch.object(
                type(self.WizardAccountX),
                "_get_url_authorize",
                return_value={
                    "type": "ir.actions.act_url",
                    "url": "https://auth.example",
                },
            ),
        ):
            res = self.WizardAccountX._action_add_account()
        mock_super.assert_called_once_with()
        self.assertEqual(
            res, {"type": "ir.actions.act_url", "url": "https://auth.example"}
        )

    @patch(PATCH_REQUEST_POST)
    @patch(PATCH_WIZARD_ACCOUNT.format("_get_oauth"))
    def test_success_returns_act_url_and_sets_token(self, mock_get_oauth, mock_post):
        mock_get_oauth.return_value = object()
        mock_post.return_value = Mock(text="oauth_token=AAA&oauth_token_secret=BBB")
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

    @patch(PATCH_WIZARD_ACCOUNT.format("_logger"))
    @patch(PATCH_REQUEST_POST)
    @patch(PATCH_WIZARD_ACCOUNT.format("_get_oauth"))
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

    def _fake_client(self, user_id="ID123", name="User Name", username="user"):
        me = SimpleNamespace(
            data=SimpleNamespace(id=user_id, name=name, username=username)
        )
        client = Mock()
        client.get_me.return_value = me
        return client

    def test_does_nothing_if_x_account_id_already_exists(self):
        client = self._fake_client(
            user_id="FAKE123456789", name="Same", username="same"
        )

        with (
            patch.object(
                type(self.SocialAccount), "get_client_api", return_value=client
            ),
            patch.object(
                type(self.SocialAccount),
                "_get_access_token_oauth2",
                return_value="BT123",
            ) as mock_o2,
            patch.object(
                self.SocialAccount.env, "ref", return_value=SimpleNamespace(id=222)
            ) as mock_ref,
            patch.object(type(self.SocialAccount), "create") as mock_create,
            patch.object(type(self.SocialAccount), "write") as mock_write,
            patch.object(
                type(self.SocialAccount), "_notify_user_client"
            ) as mock_notify,
        ):
            self.SocialAccount.create_account_x(
                x_access_token_oauth1="AT",
                x_access_secret_oauth1="AS",
                kwargs={"oauth_token": "tok-1"},
            )
        mock_o2.assert_not_called()
        mock_ref.assert_not_called()
        mock_create.assert_not_called()
        mock_write.assert_not_called()
        mock_notify.assert_not_called()

    def test_update_account(self):
        fake_url = {
            "type": "ir.actions.act_url",
            "url": "https://example.com",
            "target": "self",
        }
        self.WizardAccountX.write({"update_keys": True})
        with patch.object(
            type(self.WizardAccount), "_get_url_authorize", return_value=fake_url
        ):
            result = self.WizardAccountX._update_account()
            self.assertEqual(result["type"], "ir.actions.act_url")
            self.assertEqual(result["url"], "https://example.com")
            self.assertEqual(result["target"], "self")

    def test_action_valid_add_account(self):
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
        with self.assertRaises(ValidationError):
            wizard_id._action_valid_add_account()
