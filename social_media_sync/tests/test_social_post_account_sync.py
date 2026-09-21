# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from unittest.mock import patch

import pytz
import requests
from freezegun import freeze_time

from odoo.fields import Command
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .test_social_sync_common import (
    PATCH_SYNC_POST_ACCOUNT,
    TestSocialMediaSyncCommon,
)

LOGGER_SYNC_POST_ACCOUNT = "odoo.addons.social_media_sync.models.social_post_account"


@tagged("post_install", "-at_install")
class TestSocialPostAccountSync(TestSocialMediaSyncCommon):
    def test_by_remote_ref_answers_only_the_account_asked_for(self):
        """Two accounts seeing the same publication keep a line each.

        The reference is what the social media answers, not what identifies a
        line: without the account in the domain the import of one account
        writes over the publication of the other.
        """
        other_account = self.SocialAccount.create(
            {
                "name": "Second Linkedin",
                "media_id": self.social_media_id.id,
            }
        )
        shared_ref = "shared-publication"
        mine = self.social_post_account_id
        mine.remote_ref = shared_ref
        theirs = self.SocialPostAccount.create(
            {
                "post_id": self.social_post_id.id,
                "account_id": other_account.id,
                "message": "Test message",
                "remote_ref": shared_ref,
            }
        )
        PostAccount = self.env["social.post.account"]
        self.assertEqual(
            PostAccount._by_remote_ref([shared_ref], self.social_account_id),
            {shared_ref: mine},
        )
        self.assertEqual(
            PostAccount._by_remote_ref([shared_ref], other_account),
            {shared_ref: theirs},
        )

    def test_by_remote_ref_reads_what_the_reader_cannot_see(self):
        """The reconciliation is not scoped by who runs the import.

        The import runs from a cron, which is not the user responsible for the
        account, and an archived line is still a line: whatever the search
        leaves out is imported again under a second publication for the same
        remote reference.
        """
        reader = self.env["res.users"].create(
            {
                "login": "social_reader",
                "name": "Social Reader",
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "social_media_base.group_social_media_user"
                            ).id,
                        ]
                    )
                ],
            }
        )
        self.social_account_id.user_id = self.env.ref("base.user_admin")
        line = self.social_post_account_id
        line.write({"remote_ref": "hidden-publication", "active": False})
        PostAccount = self.env["social.post.account"].with_user(reader)
        self.assertEqual(
            PostAccount._by_remote_ref(
                ["hidden-publication"],
                self.social_account_id,
                sudo=True,
                active_test=False,
            ),
            {"hidden-publication": line},
        )
        self.assertFalse(
            PostAccount._by_remote_ref(["hidden-publication"], self.social_account_id),
            "Without the flags the line is invisible, and the import creates "
            "a second one for the same publication.",
        )

    def test_by_remote_ref_cannot_be_asked_without_an_account(self):
        """The account is a required parameter, not a flag with a default."""
        with self.assertRaises(TypeError):
            self.env["social.post.account"]._by_remote_ref(["whatever"])

    def test_statistics_views_show_the_imported_figures(self):
        """The figures this module imports are read from the publication.

        The three views of a publication draw them only with this module
        installed, so what is checked is the arch after the inheritance.
        """
        figures = (
            "impression_count",
            "click_count",
            "share_count",
            "like_count",
            "comment_count",
            "interactions_count",
            "engagement",
        )
        for xml_id, view_type in (
            ("social_post_account_view_form_statistics", "form"),
            ("social_post_account_view_form", "form"),
            ("social_post_account_view_tree", "tree"),
        ):
            view = self.env.ref(f"social_media_base.{xml_id}")
            arch = self.env["social.post.account"].get_view(view.id, view_type)["arch"]
            for field_name in figures:
                with self.subTest(view=xml_id, field=field_name):
                    self.assertIn(f'name="{field_name}"', arch)

    def test_statistics_dialog_tells_the_two_click_numbers_apart(self):
        """Both counters are read there, and neither is called just Clicks."""
        view = self.env.ref(
            "social_media_base.social_post_account_view_form_statistics"
        )
        arch = self.env["social.post.account"].get_view(view.id, "form")["arch"]
        self.assertLess(
            arch.index('name="link_click_count"'),
            arch.index('name="click_count"'),
            msg="The clicks Odoo counted come before the ones of the media.",
        )
        self.assertIn("Tracked Clicks", arch)
        self.assertIn("Social Media Clicks", arch)

    def test_comments(self):
        result = self.social_post_account_id.create_comment({})
        self.assertIsNone(result)

        result = self.social_post_account_id.get_comments()
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {"success": False, "data": []})

    def test_get_comment_replies(self):
        """Without a connector answering, a comment has no replies to draw."""
        result = self.social_post_account_id.get_comment_replies(
            "urn:li:comment:(urn:li:activity:6666,1)"
        )
        self.assertEqual(result, {"success": False, "data": [], "count": 0})

    def test_the_connectors_do_not_rewrite_a_foreign_answer(self):
        """What the chain says about another social media travels back whole.

        Every connector extends these three hooks and answers only for its own
        ``media_type``, so a publication none of them serves is told exactly
        what this module has to say — ``success`` and ``message`` included, not
        just ``data``. The answer asserted is one no connector builds, so a
        link rewriting it is seen even when the shape it writes back matches
        the default of the hook.
        """
        answer = {
            "success": False,
            "message": "Only the media of the publication answers.",
            "data": [{"id": "foreign"}],
            "count": 0,
        }
        for hook, args in (
            ("get_comments", ()),
            ("get_comment_replies", ("urn:li:comment:(urn:li:activity:6666,1)",)),
            ("create_comment", ({"body": "Test Comment"},)),
        ):
            with (
                self.subTest(hook=hook),
                patch(PATCH_SYNC_POST_ACCOUNT.format(hook), return_value=answer),
            ):
                self.assertEqual(
                    getattr(self.social_post_account_id, hook)(*args),
                    answer,
                    msg=f"{hook} rewrote what another social media answered.",
                )

    @freeze_time("2025-05-30 12:00:00")
    def test_format_published_time_says_how_long_ago(self):
        """A moment carrying its time zone is answered as a sentence."""
        published = datetime(2025, 5, 27, 12, 0, 0, tzinfo=pytz.utc)
        self.assertEqual(
            self.social_post_account_id._format_published_time(published),
            "3 days ago",
        )

    @freeze_time("2025-05-30 12:00:00")
    def test_format_published_time_reads_a_naive_moment_as_utc(self):
        """A moment without a time zone is the one Odoo stores, and it is UTC."""
        self.assertEqual(
            self.social_post_account_id._format_published_time(
                datetime(2025, 5, 27, 12, 0, 0)
            ),
            "3 days ago",
        )

    @freeze_time("2025-05-30 12:00:00")
    def test_format_published_time_gives_one_unit(self):
        """Babel answers the largest unit that fits, never two of them."""
        published = datetime(2023, 2, 28, 12, 0, 0, tzinfo=pytz.utc)
        self.assertEqual(
            self.social_post_account_id._format_published_time(published),
            "2 years ago",
        )

    def test_format_published_time_without_a_moment(self):
        """A comment the social media did not stamp is drawn without a date."""
        self.assertEqual(self.social_post_account_id._format_published_time(False), "")

    def test_action_like_comment(self):
        result = self.SocialPostAccount.action_like_comment()
        self.assertEqual(
            result,
            {"success": True, "message": "", "post_deleted": False, "liked": True},
        )

    def test_action_unlike_hooks(self):
        """Withdrawing a reaction is a hook of its own, and answers the same."""
        self.assertEqual(
            self.SocialPostAccount.action_unlike_comment(),
            {"success": True, "message": "", "post_deleted": False, "liked": False},
        )
        self.assertEqual(
            self.SocialPostAccount.action_unlike_post(),
            {"success": True, "message": "", "post_deleted": False, "liked": False},
        )

    def test_map_medias_account_keeps_nothing_when_the_download_fails(self):
        """A failed download must not attach anything.

        Otherwise the publication would hold an empty attachment that the
        next synchronization has no reason to replace.
        """
        response = patch("requests.get")
        with mute_logger(LOGGER_SYNC_POST_ACCOUNT), response as mock_get:
            mock_get.return_value.status_code = 500
            self.assertFalse(
                self.social_post_account_id._map_medias_account(
                    **{"name": "urn:li:image:1", "url": "https://fake/1.jpg"}
                )
            )
        self.assertFalse(
            self.social_post_account_id._get_medias_account(["urn:li:image:1"])
        )

    def test_map_medias_account_survives_a_request_exception(self):
        with mute_logger(LOGGER_SYNC_POST_ACCOUNT), patch(
            "requests.get", side_effect=requests.exceptions.RequestException("boom")
        ):
            self.assertFalse(
                self.social_post_account_id._map_medias_account(
                    **{"name": "urn:li:image:2", "url": "https://fake/2.jpg"}
                )
            )

    def test_map_medias_account_needs_a_url(self):
        """The bridges skip a media reported without a download URL."""
        with self.assertRaises(KeyError):
            self.social_post_account_id._map_medias_account(
                **{"name": "urn:li:image:local", "datas": self.image_base64}
            )

    def test_get_medias_account_of_an_empty_recordset(self):
        """The import asks before the publication exists."""
        self.assertEqual(
            self.SocialPostAccount._get_medias_account(["urn:li:image:1"]), []
        )

    def test_get_medias_account_does_not_see_another_publication(self):
        """The same image gives a different reference on each account.

        Two publications of one post share the attachment, so the answer can
        only come from the publication being asked.
        """
        attachment = self.env["ir.attachment"].create(
            {
                "name": "shared.png",
                "type": "binary",
                "datas": b"ZmFrZS1pbWFnZQ==",
            }
        )
        other_account = self.SocialAccount.create(
            {
                "name": "Linkedin second account",
                "media_id": self.social_media_id.id,
                "username": "linkedin_second_account",
            }
        )
        first = self.social_post_account_id
        second = self.SocialPostAccount.create(
            {
                "message": "Same image, other account",
                "account_id": other_account.id,
            }
        )
        for post_account, urn in (
            (first, "urn:li:image:A"),
            (second, "urn:li:image:B"),
        ):
            post_account.write(
                {
                    "image_ids": [Command.set(attachment.ids)],
                    "media_refs": {str(attachment.id): urn},
                }
            )
        self.assertEqual(
            first._get_medias_account(["urn:li:image:A", "urn:li:image:B"]),
            ["urn:li:image:A"],
        )
        self.assertEqual(
            second._get_medias_account(["urn:li:image:A", "urn:li:image:B"]),
            ["urn:li:image:B"],
        )

    def test_get_medias_account_finds_medias_for_a_manager(self):
        """A manager synchronizing another user's account gets the same answer.

        The medias already stored are read from the publication itself, and a
        manager sees every publication, so running the synchronization on
        somebody else's account does not download a duplicate. A plain user
        cannot reach the publication at all, which is what the record rule of
        ``social.post.account`` is for.
        """
        attachment = self.env["ir.attachment"].create(
            {
                "name": "shared.png",
                "type": "binary",
                "res_model": "social.post.account",
                "res_id": self.social_post_account_id.id,
                "datas": b"ZmFrZS1pbWFnZQ==",
            }
        )
        self.social_post_account_id.write(
            {
                "image_ids": [Command.set(attachment.ids)],
                "media_refs": {str(attachment.id): "urn:li:image:SHARED"},
            }
        )
        manager = self.env["res.users"].create(
            {
                "name": "Other social manager",
                "login": "other_media_manager_sync_test",
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "social_media_base.group_social_media_manager"
                            ).id,
                        ]
                    )
                ],
            }
        )
        self.assertEqual(
            self.social_post_account_id.with_user(manager)._get_medias_account(
                ["urn:li:image:SHARED"]
            ),
            ["urn:li:image:SHARED"],
            "The medias already downloaded must be found whoever runs the "
            "synchronization, otherwise every run creates a duplicate",
        )

    def test_the_statistics_dialog_belongs_to_the_base(self):
        """This module no longer draws the figures of a publication.

        They are read back by the connectors for the recent publications, so
        the dialog is drawn by ``social_media_base`` alone. What this module
        still adds are the views that span the whole history.
        """
        self.assertFalse(
            self.env.ref(
                "social_media_sync.social_post_account_view_form_statistics_inherit",
                raise_if_not_found=False,
            )
        )
        arch = self.SocialPostAccount.get_view(
            self.env.ref(
                "social_media_base.social_post_account_view_form_statistics"
            ).id
        )["arch"]
        for field_name in (
            "impression_count",
            "click_count",
            "share_count",
            "like_count",
            "comment_count",
            "interactions_count",
            "engagement",
            "statistics_date",
        ):
            self.assertIn(f'name="{field_name}"', arch)
