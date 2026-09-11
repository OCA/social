# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, patch

from odoo.addons.base.tests.common import BaseCommon

PATCH_SOCIAL_BAS_MODELS = "odoo.addons.social_media_base.models"
PATCH_SOCIAL_WIZARDS = "odoo.addons.social_media_base.wizards"
PATCH_SOCIAL_BASE_MIXIN = "{}.social_media_base_mixin.SocialMediaBaseMixin.{}".format(
    PATCH_SOCIAL_BAS_MODELS, "{}"
)
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
PATCH_LINK_TRACKER = "odoo.addons.link_tracker.models.link_tracker.LinkTracker.{}"
# The ``request`` the mixin reads to keep a message in the session. Patched by
# every module that has to prove which of the two channels a message took.
PATCH_MIXIN_REQUEST = f"{PATCH_SOCIAL_BAS_MODELS}.social_media_base_mixin.request"
TEST_BASE_URL = "http://testserver"


class TestSocialMediaBaseCommon(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("en_US")
        cls.env = cls.env(context=dict(cls.env.context, lang="en_US"))
        cls.image_base64 = base64.b64encode(b"testimage").decode("utf-8")
        cls.video_data = base64.b64encode(b"testvideo").decode("utf-8")
        cls.SocialMedia = cls.env["social.media"]
        cls.SocialMediaBaseMixin = cls.env["social.media.base.mixin"]
        cls.IrConfigParameter = cls.env["ir.config_parameter"]
        cls.ResConfigSettings = cls.env["res.config.settings"]
        cls.SocialAccount = cls.env["social.account"]
        cls.SocialPost = cls.env["social.post"]
        cls.SocialPostAccount = cls.env["social.post.account"]
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
        # A link tracker reads the title of the url it shortens, which is an
        # outbound request, and the short urls are built from the base url.
        cls.env["ir.config_parameter"].sudo().set_param("web.base.url", TEST_BASE_URL)
        title_patcher = patch(
            PATCH_LINK_TRACKER.format("_get_title_from_url"),
            side_effect=lambda url: url,
        )
        cls.startClassPatcher(title_patcher)
        cls.test_message = "Test Message"
        cls.start_datetime = datetime(2025, 1, 1)
        cls.end_datetime = datetime(2025, 1, 31)
        cls.start_timestamp = 1735689600000
        cls.end_timestamp = 1738281600000

    @contextmanager
    def _fake_media_types(self, **media_by_type):
        """Give the social media a ``media_type`` without a connector installed.

        ``social.media.media_type`` is an empty ``Selection`` that every
        connector extends, so base cannot write a real value into it without
        depending on a connector being installed. The values are faked for the
        duration of the block and written on the records passed by keyword,
        ``alpha=self.social_media_id`` writing ``"alpha"`` on that media.
        """
        field = self.SocialMedia._fields["media_type"]
        selection = [(media_type, media_type) for media_type in media_by_type]
        with patch.object(field, "selection", new=selection):
            for media_type, media in media_by_type.items():
                media.write({"media_type": media_type})
            yield

    def dashboard_publication(self, media, account_name, message):
        """Create a publication the dashboard of the tours draws.

        The kanban is scoped by ``user_id`` and reads what a social media
        reported, so the account belongs to the user the tour logs in as and
        the publication carries the url and the figures the footer says.

        :param media: the ``social.media`` of the account.
        :param str account_name: name of the account, which titles its column.
        :param str message: the message of the publication, which is what the
            tour looks the card up by.
        :rtype: odoo.api.Model
        """
        user = self.env.ref("base.user_admin")
        user.sudo().write(
            {
                "groups_id": [
                    (
                        4,
                        self.env.ref("social_media_base.group_social_media_manager").id,
                    )
                ]
            }
        )
        account = self.SocialAccount.create(
            {
                "name": account_name,
                "media_id": media.id,
                "remote_ref": "tour-account",
                "user_id": user.id,
            }
        )
        post = self.SocialPost.create(
            {
                "message": message,
                "account_ids": [(6, 0, account.ids)],
                "user_id": user.id,
            }
        )
        return self.SocialPostAccount.create(
            {
                "post_id": post.id,
                "account_id": account.id,
                "message": message,
                "state": "posted",
                "remote_ref": "tour-publication",
                "post_account_url": "http://testserver/tour-publication",
                "published_date": "2025-01-01 10:00:00",
                "like_count": 7,
                "comment_count": 2,
            }
        )

    def _get_parent_class_defining(self, record, method_name):
        mro = type(record).mro()
        for parent in mro[1:]:
            if method_name in parent.__dict__:
                return parent
        raise AssertionError(  # pragma: no cover
            f"Not found method '{method_name}'"
        )

    def valid_action_open_account_media(self, media_id, action):
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "wizard.social.account")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["views"], [[False, "form"]])
        self.assertIn("context", action)
        self.assertEqual(action["context"], {"default_media_id": media_id.id})

    def valid_not_action_open_account_media(self):
        parent_cls = self._get_parent_class_defining(
            self.SocialMedia, "action_open_account"
        )
        fake_action_account = {
            "type": "ir.actions.act_window",
            "res_model": "wizard.social.account",
            "views": [[False, "form"]],
            "target": "new",
        }
        with patch.object(
            parent_cls,
            "action_open_account",
            autospec=True,
            return_value=fake_action_account,
        ) as mocked:
            action = self.SocialMedia.action_open_account()
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
