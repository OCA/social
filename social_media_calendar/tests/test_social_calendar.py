# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)


class TestSocialMediaCalendar(TestSocialMediaBaseCommon):
    def test_compute_color(self):
        mapping = {
            "planned": 2,
            "publishing": 6,
            "published": 10,
            "cancelled": 0,
            "draft": 4,
        }

        for state, expected_color in mapping.items():
            post = self.SocialPost.create({"message": f"Post {state}", "state": state})
            self.assertEqual(
                post.color,
                expected_color,
                f"State {state!r} should map to color {expected_color}",
            )
