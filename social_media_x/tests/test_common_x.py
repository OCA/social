# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from tweepy.errors import TooManyRequests

from odoo.fields import Command

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

PATCH_ACCOUNT_X = "odoo.addons.social_media_x.models.social_account.{}"
PATCH_SOCIAL_X_WIZARDS = "odoo.addons.social_media_x.wizards"
PATCH_POST_ACCOUNT_X = (
    "odoo.addons.social_media_x.models." "social_post_account.SocialPostAccount.{}"
)
PACTH_MEDIA_MODELS_X = "odoo.addons.social_media_x.models.{}"
PATCH_MEDIA_X = PACTH_MEDIA_MODELS_X.format("social_media.SocialMedia.{}")

PATCH_X_UTILS = "odoo.addons.social_media_x.social_x_utils.{}"
PATCH_REQUEST_POST = PATCH_ACCOUNT_X.format("requests.post")

PATCH_WIZARD_ACCOUNT_X = "{}.wizard_social_account.{}".format(
    PATCH_SOCIAL_X_WIZARDS, "{}"
)


class TestSocialCommonX(TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_x_id = cls.SocialMedia.create(
            {
                "name": "X",
                "media_type": "x",
            }
        )

        account_values = {
            "name": "X Account",
            "media_id": cls.media_x_id.id,
            "access_token": "fake-token",
            "x_account_id": "FAKE123456789",
            "username": "fake-username",
        }

        cls.SocialAccountX = cls.SocialAccount.create(account_values)

        account_values.update(
            {
                "x_api_key": "TEST_KEY",
                "x_api_secret": "TEST_SECRET",
            }
        )

        cls.SocialAccountCredentialX = cls.SocialAccount.create(account_values)

        cls.SocialPostX = cls.SocialPost.create(
            {
                "message": "Test Message",
                "account_ids": [Command.set(cls.SocialAccountX.ids)],
            }
        )

        post_account = {
            "message": "Test Message",
            "account_id": cls.SocialAccountX.id,
            "media_id": cls.media_x_id.id,
            "post_id": cls.SocialPostX.id,
            "state": "posted",
            "x_post_account_id": "159753456",
        }

        cls.SocialPostAccountX = cls.SocialPostAccount.create(post_account)
        cls.WizardAccountX = cls.WizardAccount.create(
            {
                "x_api_key": "TEST_KEY",
                "x_api_secret": "TEST_SECRET",
                "media_id": cls.media_x_id.id,
            }
        )

        cls.SocialAccountEmptyX = cls.SocialAccount.create(
            {
                "name": "Twitter",
                "x_api_key": False,
                "x_api_secret": False,
                "x_access_token_oauth1": False,
                "x_access_secret_oauth1": False,
                "x_access_token_oauth2": False,
            }
        )
        cls.admin_media_x_admin = mail_new_test_user(
            cls.env,
            groups="base.group_user,base.group_system",
            login="admin_media_x_admin",
            name="Admin Media X Admin",
            signature="--\nMEDIAX",
        )

    def get_exception_manyrequests(self):
        fake_resp = MagicMock()
        fake_resp.headers = {
            "x-rate-limit-limit": "1",
            "x-rate-limit-remaining": "0",
            "x-rate-limit-reset": "9999999999",
        }
        return TooManyRequests(response=fake_resp)

    def get_patch_exceptions_x(
        self, fake_client, many_requests=False, valid_time_request=True
    ):
        patch_client = patch.object(
            type(self.SocialPostAccountX.account_id),
            "get_client_api",
            autospec=True,
            return_value=fake_client,
        )
        if not many_requests and not valid_time_request:
            return patch_client
        result_patch = [patch_client]
        if valid_time_request:
            result_patch.append(
                patch.object(
                    type(self.SocialPostAccountX.account_id),
                    "_valid_time_request",
                    autospec=True,
                    return_value=True,
                )
            )
        if many_requests:
            result_patch.append(
                patch.object(
                    type(self.SocialPostAccountX.account_id),
                    "_get_message_many_requests",
                    autospec=True,
                    return_value=False,
                )
            )
        result = result_patch if len(result_patch) > 1 else result_patch[0]
        return tuple(result)