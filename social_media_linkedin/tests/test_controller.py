# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase

from odoo.addons.social_media_linkedin.controllers.social_media_linkedin import (
    SocialMediaLinkedin,
)


class TestSocialController(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.controller = SocialMediaLinkedin()

    def test_social_linkedin_webhook(self):
        controller = SocialMediaLinkedin()
        result = controller.social_linkedin_webhook()
        self.assertTrue(result)
