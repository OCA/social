# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import ValidationError

from odoo.addons.social_media_x.tests.test_common_x import (
    TestSocialCommonX,
)


class TestSocialPostX(TestSocialCommonX):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_check_account_ids(self):
        account_repeat_username = self.SocialAccountCredentialX.copy()
        with self.assertRaises(ValidationError):
            self.SocialPost.create(
                {
                    "message": "Test Message",
                    "account_ids": [
                        Command.set(
                            [
                                self.SocialAccountCredentialX.id,
                                account_repeat_username.id,
                            ]
                        )
                    ],
                }
            )
