# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)
from odoo.addons.social_media_calendar import POST_ACTION_VIEW_MODE, uninstall_hook


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

    def test_compute_date_calendar_fallbacks(self):
        post = self.SocialPost.create({"message": "Calendar post"})
        self.assertEqual(post.date_calendar, post.create_date)
        post.write({"send_post": "schedule"})
        self.assertEqual(post.date_calendar, post.send_post_date)
        post.write({"published_date": "2030-06-20 10:00:00"})
        self.assertEqual(str(post.date_calendar), "2030-06-20 10:00:00")

    def test_date_calendar_keeps_the_time_of_the_user(self):
        self.env.user.tz = "Europe/Madrid"
        post = self.SocialPost.create({"message": "Late post"})
        post.write({"published_date": "2026-07-20 22:30:00"})
        self.assertEqual(
            fields.Datetime.context_timestamp(post, post.date_calendar).strftime(
                "%Y-%m-%d"
            ),
            "2026-07-21",
            msg="The calendar must place the post on the day the user sees, "
            "not on the UTC one.",
        )

    def test_post_action_includes_calendar_view(self):
        action = self.env.ref("social_media_base.social_post_action")
        self.assertIn("calendar", action.view_mode)

    def test_uninstall_hook_restores_the_post_action(self):
        action = self.env.ref("social_media_base.social_post_action")
        uninstall_hook(self.env)
        self.assertEqual(action.view_mode, POST_ACTION_VIEW_MODE)
        action.view_mode = "kanban,calendar,tree,form"
