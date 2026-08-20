# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from datetime import datetime
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase

PATCH_SOCIAL_BASE_UTILS = "odoo.addons.social_media_base.social_utils.{}"
PATCH_SOCIAL_BAS_MODELS = "odoo.addons.social_media_base.models"
PATCH_SOCIAL_WIZARDS = "odoo.addons.social_media_base.wizards"
PATCH_SOCIAL_BASE_MIXIN = "{}.social_media_base_mixin.SocialMediaBaseMixin.{}".format(
    PATCH_SOCIAL_BAS_MODELS, "{}"
)
PATCH_POST = "{}.social_post.SocialPost.{}".format(PATCH_SOCIAL_BAS_MODELS, "{}")
PATCH_POST_ACCOUNT = "{}.social_post_account.SocialPostAccount.{}".format(
    PATCH_SOCIAL_BAS_MODELS, "{}"
)
PATCH_MEDIA = "{}.social_media.SocialMedia.{}".format(PATCH_SOCIAL_BAS_MODELS, "{}")
PATCH_ACCOUNT = "{}.social_account.SocialAccount.{}".format(
    PATCH_SOCIAL_BAS_MODELS, "{}"
)
PATCH_WIZARD_ACCOUNT = "{}.wizard_social_account.WizardSocialAccount.{}".format(
    PATCH_SOCIAL_WIZARDS, "{}"
)


class TestSocialMediaBaseCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.image_base64 = base64.b64encode(b"testimage").decode("utf-8")
        cls.video_data = base64.b64encode(b"testvideo").decode("utf-8")
        cls.SocialMedia = cls.env["social.media"]
        cls.SocialMediaBaseMixin = cls.env["social.media.base.mixin"]
        cls.IrConfigParameter = cls.env["ir.config_parameter"]
        cls.ResConfigSettings = cls.env["res.config.settings"]
        cls.SocialAccount = cls.env["social.account"]
        cls.SocialPost = cls.env["social.post"]
        cls.SocialPostAccount = cls.env["social.post.account"]
        cls.UtmGroupCampaign = cls.env["utm.group.campaign"]
        cls.UtmCampaign = cls.env["utm.campaign"]
        cls.WizardAccount = cls.env["wizard.social.account"]
        cls.social_media_id = cls.SocialMedia.create(
            {
                "name": "Linkedin",
            }
        )
        cls.social_account_id = cls.SocialAccount.create(
            {
                "name": "Linkedin",
                "media_id": cls.social_media_id.id,
            }
        )
        cls.social_post_id = cls.SocialPost.create(
            {
                "message": "Test message",
                "account_ids": [(6, 0, [cls.social_account_id.id])],
            }
        )
        cls.social_post_account_id = cls.SocialPostAccount.create(
            {
                "post_id": cls.social_post_id.id,
                "account_id": cls.social_account_id.id,
                "message": "Test message",
            }
        )
        cls.test_message = "Test Message"
        cls.start_datetime = datetime(2025, 1, 1)
        cls.end_datetime = datetime(2025, 1, 31)
        cls.start_timestamp = 1735689600000
        cls.end_timestamp = 1738281600000

    def _get_parent_class_defining(self, record, method_name):
        mro = type(record).mro()
        for parent in mro[1:]:
            if method_name in parent.__dict__:
                return parent
        raise AssertionError(f"Not found method '{method_name}'")

    def valid_open_action_account_media(self, media_id, action):
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "wizard.social.account")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["views"], [[False, "form"]])
        self.assertIn("context", action)
        self.assertEqual(action["context"], {"default_media_id": media_id.id})

    def valid_not_open_action_account_media(self):
        parent_cls = self._get_parent_class_defining(
            self.SocialMedia, "open_action_account"
        )
        fake_action_account = {
            "type": "ir.actions.act_window",
            "res_model": "wizard.social.account",
            "views": [[False, "form"]],
            "target": "new",
        }
        with patch.object(
            parent_cls,
            "open_action_account",
            autospec=True,
            return_value=fake_action_account,
        ) as mocked:
            action = self.SocialMedia.open_action_account()
            mocked.assert_called_once()
            self.assertEqual(action, fake_action_account)

    def generate_magic_mock(self, **values):
        new_mock = MagicMock()
        if values.get("status_code", False):
            new_mock.status_code = values["status_code"]
        if values.get("return_value", False):
            new_mock.return_value = values["return_value"]
        if values.get("json_return_value", False):
            new_mock.json.return_value = values["json_return_value"]
        return new_mock

    def generate_patch(self, **values):
        new_patch = None
        model_patch = values.get("model_patch", False)
        side_effect = values.get("side_effect", False)
        return_value = values.get("return_value", False)

        if values.get("type_object", False):
            if side_effect:
                new_patch = patch.object(
                    type(model_patch),
                    values.get("method_patch", False),
                    autospec=True,
                    side_effect=side_effect,
                )
            elif return_value:
                new_patch = patch.object(
                    type(model_patch),
                    values.get("method_patch", False),
                    autospec=True,
                    return_value=return_value,
                )
        else:
            if side_effect:
                new_patch = patch(
                    values.get("model_patch", False),
                    autospec=True,
                    side_effect=side_effect,
                )
            elif return_value:
                new_patch = patch(
                    values.get("model_patch", False),
                    autospec=True,
                    return_value=return_value,
                )

        return new_patch
