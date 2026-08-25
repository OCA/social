# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


import base64
from unittest.mock import patch

from odoo.fields import Command
from odoo.tools import hmac

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

PATCH_WIZARD_LINKEDIN = "odoo.addons.social_media_linkedin.wizards.{}"
PATCH_WIZARD_ACCOUNT_LINKEDIN = PATCH_WIZARD_LINKEDIN.format("wizard_social_account.{}")

PATCH_ACCOUNT_LINKEDIN = (
    "odoo.addons.social_media_linkedin.models.social_account.SocialAccount.{}"
)
PATCH_POST_ACCOUNT_LINKEDIN = (
    "odoo.addons.social_media_linkedin.models."
    "social_post_account.SocialPostAccount.{}"
)


class LinkedinMockMixin:
    def _mock_linkedin(self, return_value, account, attribute="_request_linkedin"):
        return patch.object(type(account), attribute, return_value=return_value)


class TestSocialCommonLinkedin(LinkedinMockMixin, TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.VALID_PNG_B64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQYV2NgYGBgAAAA"
            "BAABJzQnCgAAAABJRU5ErkJggg=="
        )
        cls.WizardAccount = cls.env["wizard.social.account"]
        cls.wizard_account_id = cls.WizardAccount.create(
            {
                "media_id": cls.env.ref(
                    "social_media_linkedin.social_media_linkedin"
                ).id,
                "csrf_state_token": "fake-csrf-token",
                "linkedin_client": "fake-client-id",
                "linkedin_secret": "fake-secret",
            }
        )
        cls.url_callback = f"{cls.wizard_account_id.get_base_url()}/linkedin/callback"
        cls.media_linkedin_id = cls.SocialMedia.create(
            {
                "name": "linkedin",
                "media_type": "linkedin",
            }
        )

        cls.SocialAccountLinkedin = cls.SocialAccount.create(
            {
                "name": "Linkedin Account",
                "media_id": cls.media_linkedin_id.id,
                "remote_ref": "urn:li:organization:123456",
                "access_token": "fake-token",
                "linkedin_client_id": "fake-client-id",
                "linkedin_secret": "fake-secret",
            }
        )

        cls.SocialAccountLinkedinData = cls.SocialAccount.create(
            {
                "name": "Linkedin Account",
                "media_id": cls.env.ref(
                    "social_media_linkedin.social_media_linkedin"
                ).id,
                "remote_ref": "urn:li:organization:123456890",
                "access_token": "fake-token",
            }
        )

        cls.SocialPostLinkedin = cls.SocialPost.create(
            {
                "message": "Test Message",
                "account_ids": [Command.set(cls.SocialAccountLinkedin.ids)],
            }
        )

        post_account = {
            "message": "Test Message",
            "account_id": cls.SocialAccountLinkedin.id,
            "media_id": cls.media_linkedin_id.id,
            "post_id": cls.SocialPostLinkedin.id,
            "remote_ref": "1234567890",
            "state": "posted",
        }

        cls.SocialPostAccountLinkedin = cls.SocialPostAccount.create(post_account)

        post_account.update(
            {
                "state": "ready",
                "remote_ref": False,
            }
        )
        cls.SocialPostAccountReadyLinkedin = cls.SocialPostAccount.create(post_account)

    def create_attachment(self, attach_name="test_exist_image.jpg", size=None):
        """Create an attachment of a given name, and optionally of a size.

        The mimetype is guessed from the name by ``ir.attachment`` itself, and
        the size is the length of the content, so a test about a limit has to
        write the bytes: ``file_size`` is dropped from the values on write.

        :param str attach_name: name of the file, which decides its mimetype.
        :param int size: number of bytes the attachment weighs.
        :rtype: odoo.api.Model
        """
        content = b"\0" * size if size else b"existing"
        return self.env["ir.attachment"].create(
            {
                "name": attach_name,
                "type": "binary",
                "datas": base64.b64encode(content).decode(),
                "res_model": "social.post.account",
                "res_id": self.SocialPostAccountLinkedin.id,
            }
        )

    def generate_code(self, code_generated="fake-code-token"):
        return hmac(
            self.env(su=True),
            f"{self.media_linkedin_id.media_type}-account-{code_generated}-csrf-token",
            self.media_linkedin_id.id,
        )

    def get_patch_exceptions_linkedin(self, fake_client=False, side_effect=False):
        if side_effect:
            return patch.object(
                type(self.SocialAccountLinkedin),
                "_request_linkedin",
                autospec=True,
                side_effect=side_effect,
            )
        return patch.object(
            type(self.SocialAccountLinkedin),
            "_request_linkedin",
            autospec=True,
            return_value=fake_client,
        )
