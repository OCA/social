# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from lxml import etree

from odoo import fields
from odoo.fields import Command

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)


class TestSocialMediaCalendar(TestSocialMediaBaseCommon):
    def test_compute_color(self):
        mapping = {
            "planned": 2,
            "publishing": 6,
            "partially_published": 3,
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

    def test_default_get_proposes_the_day_clicked_on_the_calendar(self):
        clicked_date = fields.Datetime.now() + timedelta(days=3)
        defaults = self.SocialPost.with_context(
            default_date_calendar=clicked_date
        ).default_get(["send_post", "send_post_date"])
        self.assertEqual(defaults["send_post"], "schedule")
        self.assertEqual(defaults["send_post_date"], clicked_date)

    def test_a_post_created_from_the_calendar_is_planned_on_that_day(self):
        clicked_date = fields.Datetime.now() + timedelta(days=3)
        SocialPost = self.SocialPost.with_context(default_date_calendar=clicked_date)
        post = SocialPost.create(
            {
                "message": "Post from the calendar",
                "account_ids": [Command.set([self.social_account_id.id])],
                **SocialPost.default_get(["send_post", "send_post_date"]),
            }
        )
        self.assertEqual(post.state, "planned")
        self.assertEqual(post.date_calendar, clicked_date)

    def test_default_get_ignores_a_day_already_past(self):
        """A past date would be published by the cron on its next run."""
        clicked_date = fields.Datetime.now() - timedelta(days=1)
        SocialPost = self.SocialPost.with_context(default_date_calendar=clicked_date)
        defaults = SocialPost.default_get(["send_post", "send_post_date"])
        self.assertEqual(defaults["send_post"], "schedule")
        self.assertNotIn("send_post_date", defaults)
        post = SocialPost.create(
            {
                "message": "Post from a past day",
                "account_ids": [Command.set([self.social_account_id.id])],
                **defaults,
            }
        )
        self.assertGreater(post.send_post_date, fields.Datetime.now())

    def test_default_get_without_a_click_on_the_calendar(self):
        defaults = self.SocialPost.default_get(["send_post", "send_post_date"])
        self.assertEqual(defaults["send_post"], "now")
        self.assertNotIn("send_post_date", defaults)

    def test_calendar_view_lets_the_user_create_a_post(self):
        """Creating opens the form: the post needs its accounts and message."""
        view = self.env.ref("social_media_calendar.social_post_view_calendar")
        arch = etree.fromstring(view.arch)
        self.assertEqual(arch.get("create"), "1")
        self.assertEqual(arch.get("quick_create"), "0")

    def test_calendar_popover_renders_the_attachments_of_the_post(self):
        """A bare x2many renders nothing on the popover: it needs a widget."""
        view = self.env.ref("social_media_calendar.social_post_view_calendar")
        arch = etree.fromstring(view.arch)
        for field_name in ("image_ids", "video_ids"):
            node = arch.find(f".//field[@name='{field_name}']")
            self.assertIsNotNone(node, f"{field_name} is missing from the calendar")
            self.assertEqual(node.get("widget"), "many2many_tags")

    def test_post_action_includes_calendar_view(self):
        action = self.env.ref("social_media_base.social_post_action")
        self.assertEqual(
            [mode for __, mode in action.views],
            ["kanban", "calendar", "tree", "form"],
            msg="The calendar must be offered right after the kanban, which "
            "stays the default view of the action.",
        )

    def test_post_action_keeps_the_calendar_on_an_update_of_the_base(self):
        """The calendar must not depend on the ``view_mode`` of the action.

        That field belongs to ``social_media_base`` and is rewritten every
        time that module is updated on its own.
        """
        action = self.env.ref("social_media_base.social_post_action")
        action.view_mode = "kanban,tree,form"
        self.assertIn(
            "calendar",
            [mode for __, mode in action.views],
        )

    def test_post_check_messages_stay_empty(self):
        """A module adding no rule of its own objects to nothing.

        The calendar only adds views over the posts, so both fields answer
        what base answers: nothing.
        """
        self.assertFalse(self.social_post_id.message_error)
        self.assertFalse(self.social_post_id.message_info)
        self.assertEqual(self.social_post_id._get_post_errors("linkedin"), [])
        self.assertEqual(self.social_post_id._get_post_warnings("linkedin"), [])
