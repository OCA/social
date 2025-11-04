# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase

PATCH_SOCIAL_BASE_UTILS = "odoo.addons.social_media_base.social_utils.{}"
PATCH_SOCIAL_BAS_MODELS = "odoo.addons.social_media_base.models"
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


class TestSocialMediaBaseCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
