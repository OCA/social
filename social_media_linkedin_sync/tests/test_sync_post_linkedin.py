# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from datetime import datetime
from unittest.mock import MagicMock, patch
from urllib.parse import quote

from freezegun import freeze_time

from odoo import Command
from odoo.tools import mute_logger

from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
)
from odoo.addons.social_media_sync.tests.test_social_sync_common import (
    PATCH_SYNC_POST_ACCOUNT,
)

from .test_sync_linkedin_common import (
    PATCH_SYNC_ACCOUNT_LINKEDIN,
    PATCH_SYNC_POST_ACCOUNT_LINKEDIN,
    TestSocialSyncCommonLinkedin,
)

LOGGER_POST_ACCOUNT_SYNC_LINKEDIN = (
    "odoo.addons.social_media_linkedin_sync.models.social_post_account"
)


class TestSocialSyncPostLinkedin(TestSocialSyncCommonLinkedin):
    """Comments, reactions and remote verification of a LinkedIn publication."""

    @patch("odoo.addons.social_media_sync.models.social_post_account.requests.get")
    def test_get_assets_save(self, mock_get):
        """Only the images that are not stored yet are downloaded."""
        fake_content = b"fake image data"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fake_content
        mock_get.return_value = mock_response
        stored = self.create_attachment(attach_name="exists.jpg")
        self.SocialPostAccountLinkedin.write(
            {
                "image_ids": [Command.set(stored.ids)],
                "media_refs": {str(stored.id): "urn:li:image:exists"},
            }
        )
        content = {
            "multiImage": {
                "images": [
                    {"id": "urn:li:image:new"},
                    {"id": "urn:li:image:exists"},
                ]
            }
        }
        images_response = MagicMock()
        images_response.status_code = 200
        images_response.json.return_value = {
            "results": {"urn:li:image:new": {"downloadUrl": "https://fake-url/new.jpg"}}
        }
        with patch.object(
            type(self.SocialAccountLinkedin),
            "_request_linkedin",
            return_value=images_response,
        ) as mock_request_linkedin:
            attachments, media_refs = self.SocialPostAccountLinkedin._get_assets_save(
                content
            )
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments.name, "urn:li:image:new")
        self.assertEqual(attachments.datas, base64.b64encode(fake_content))
        self.assertEqual(
            media_refs,
            {str(attachments.id): "urn:li:image:new"},
            "The downloaded image is stored with the URN it has on LinkedIn",
        )
        self.assertEqual(
            mock_request_linkedin.call_args.kwargs["params_values"]["ids"],
            ["urn:li:image:new"],
        )

    def test_get_assets_save_single_image(self):
        """The image of a post with a single media is resolved as well."""
        content = {"media": {"id": "urn:li:image:single"}}
        with patch.object(
            type(self.SocialAccountLinkedin),
            "_get_linkedin_images_download_url",
            return_value={},
        ) as mock_download_url:
            attachments, media_refs = self.SocialPostAccountLinkedin._get_assets_save(
                content
            )
        self.assertFalse(attachments)
        self.assertEqual(media_refs, {})
        mock_download_url.assert_called_once_with(["urn:li:image:single"])

    def test_get_assets_save_without_images(self):
        """A post with a video or without media does not ask for any image."""
        with patch.object(
            type(self.SocialAccountLinkedin),
            "_get_linkedin_images_download_url",
        ) as mock_download_url:
            self.assertEqual(
                self.SocialPostAccountLinkedin._get_assets_save(
                    {"media": {"id": "urn:li:video:1"}}
                ),
                (self.env["ir.attachment"], {}),
            )
            self.assertEqual(
                self.SocialPostAccountLinkedin._get_assets_save({}),
                (self.env["ir.attachment"], {}),
            )
        mock_download_url.assert_not_called()

    def test_remove_assets_deleted_drops_the_images_gone_from_linkedin(self):
        """An image deleted on LinkedIn leaves the publication as well."""
        kept = self.create_attachment(attach_name="kept.jpg")
        gone = self.create_attachment(attach_name="gone.jpg")
        self.SocialPostAccountLinkedin.write(
            {
                "image_ids": [Command.set((kept | gone).ids)],
                "media_refs": {
                    str(kept.id): "urn:li:image:kept",
                    str(gone.id): "urn:li:image:gone",
                },
            }
        )
        content = {"multiImage": {"images": [{"id": "urn:li:image:kept"}]}}
        removed = self.SocialPostAccountLinkedin._remove_assets_deleted(content)
        self.assertEqual(self.SocialPostAccountLinkedin.image_ids, kept)
        self.assertEqual(len(removed), 1)
        self.assertFalse(gone.res_id, "The vacuum deletes what nothing owns")
        self.SocialPostAccountLinkedin.invalidate_recordset()
        self.assertEqual(
            self.SocialPostAccountLinkedin.media_refs,
            {str(kept.id): "urn:li:image:kept"},
        )

    def test_remove_assets_deleted_keeps_the_manual_attachments(self):
        """An image with no reference was attached by hand and is kept."""
        manual = self.create_attachment(attach_name="holidays.jpg")
        self.SocialPostAccountLinkedin.write({"image_ids": [Command.set(manual.ids)]})
        self.assertFalse(self.SocialPostAccountLinkedin._remove_assets_deleted({}))
        self.assertEqual(self.SocialPostAccountLinkedin.image_ids, manual)
        self.assertTrue(manual.exists())

    def test_remove_assets_deleted_drops_everything_without_remote_media(self):
        stored = self.create_attachment(attach_name="stored.jpg")
        self.SocialPostAccountLinkedin.write(
            {
                "image_ids": [Command.set(stored.ids)],
                "media_refs": {str(stored.id): "urn:li:image:stored"},
            }
        )
        self.SocialPostAccountLinkedin._remove_assets_deleted({})
        self.assertFalse(self.SocialPostAccountLinkedin.image_ids)
        self.assertFalse(stored.res_id, "The vacuum deletes what nothing owns")
        self.SocialPostAccountLinkedin.invalidate_recordset()
        self.assertFalse(self.SocialPostAccountLinkedin.media_refs)

    def test_remove_assets_deleted_keeps_the_images_still_online(self):
        stored = self.create_attachment(attach_name="stored.jpg")
        self.SocialPostAccountLinkedin.write(
            {
                "image_ids": [Command.set(stored.ids)],
                "media_refs": {str(stored.id): "urn:li:image:stored"},
            }
        )
        content = {"media": {"id": "urn:li:image:stored"}}
        self.assertFalse(self.SocialPostAccountLinkedin._remove_assets_deleted(content))
        self.assertEqual(self.SocialPostAccountLinkedin.image_ids, stored)

    def test_remove_assets_deleted_keeps_the_media_shared_with_the_post(self):
        """A media of the post leaves the card, but is never deleted."""
        shared = self.env["ir.attachment"].create(
            {
                "name": "shared.jpg",
                "type": "binary",
                "datas": base64.b64encode(b"existing").decode(),
            }
        )
        post = self.SocialPost.create(
            {
                "message": "Shared media",
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "image_ids": [Command.set(shared.ids)],
            }
        )
        line = self.SocialPostAccount.create(
            {
                "message": post.message,
                "account_id": self.SocialAccountLinkedin.id,
                "media_id": self.media_linkedin_id.id,
                "post_id": post.id,
                "remote_ref": "urn:li:share:shared",
                "state": "posted",
                "image_ids": [Command.set(shared.ids)],
                "media_refs": {str(shared.id): "urn:li:image:shared"},
            }
        )
        self.assertEqual(shared.res_model, "social.post")
        self.assertEqual(line._remove_assets_deleted({}), shared)
        self.assertFalse(line.image_ids)
        self.assertTrue(shared.exists())
        self.assertEqual(post.image_ids, shared)

    def test_remove_assets_deleted_drops_the_media_of_the_publication(self):
        """A media the publication downloaded belongs to it and is released."""
        downloaded = self.create_attachment(attach_name="downloaded.jpg")
        self.SocialPostAccountLinkedin.write(
            {
                "image_ids": [Command.set(downloaded.ids)],
                "media_refs": {str(downloaded.id): "urn:li:image:downloaded"},
            }
        )
        self.assertEqual(downloaded.res_model, "social.post.account")
        self.assertEqual(downloaded.res_id, self.SocialPostAccountLinkedin.id)
        self.SocialPostAccountLinkedin._remove_assets_deleted({})
        self.assertFalse(downloaded.res_id, "The vacuum deletes what nothing owns")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_like_post(self, mock_request):
        author_urn = "urn:li:person:abc"
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.action_like_post(author_urn=author_urn)
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "")

        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.action_like_post(author_urn=author_urn)
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "You have already reacted to this post.")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.action_like_post(author_urn=author_urn)
        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"], "The post does not exist or has been deleted."
        )
        self.assertTrue(result["post_deleted"])
        self.assertEqual(
            self.SocialPostAccountLinkedin.state,
            "deleted",
            msg="The 404 of the reaction is confirmed on the post and registered.",
        )

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = '{"message": "Internal error occurred."}'
        mock_request.return_value = mock_response

        result = self.SocialPostAccountLinkedin.action_like_post(author_urn=author_urn)
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Internal error occurred.")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_like_post_stores_the_reaction(self, mock_request):
        """What LinkedIn holds is kept on the line, so the card draws it."""
        line = self.SocialPostAccountLinkedin
        self.assertFalse(line.liked_by_account)
        created = MagicMock()
        created.status_code = 201
        mock_request.return_value = created
        result = line.action_like_post(author_urn="urn:li:person:abc")
        self.assertTrue(result["liked"])
        self.assertTrue(line.liked_by_account)

        line.liked_by_account = False
        already = MagicMock()
        already.status_code = 409
        mock_request.return_value = already
        result = line.action_like_post(author_urn="urn:li:person:abc")
        self.assertFalse(result["success"])
        self.assertTrue(
            result["liked"],
            msg="A reaction that was already there is still one to withdraw.",
        )
        self.assertTrue(line.liked_by_account)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_unlike_post(self, mock_request):
        """The reaction is addressed by the pair actor/entity and deleted."""
        line = self.SocialPostAccountLinkedin
        line.liked_by_account = True
        author_urn = "urn:li:person:abc"
        deleted = MagicMock()
        deleted.status_code = 204
        mock_request.return_value = deleted
        result = line.action_unlike_post(author_urn=author_urn)
        self.assertTrue(result["success"])
        self.assertFalse(result["liked"])
        self.assertFalse(line.liked_by_account)
        self.assertEqual(mock_request.call_args.kwargs["method"], "DELETE")
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"],
            f"/reactions/(actor:{quote(author_urn, safe='')},"
            f"entity:{quote(line.remote_ref, safe='')})",
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_unlike_post_without_reaction(self, mock_request):
        """A ``404`` with the publication alive is a reaction already gone."""
        line = self.SocialPostAccountLinkedin
        line.liked_by_account = True
        reaction_gone = MagicMock()
        reaction_gone.status_code = 404
        post_alive = MagicMock()
        post_alive.status_code = 200
        mock_request.side_effect = [reaction_gone, post_alive]
        result = line.action_unlike_post(author_urn="urn:li:person:abc")
        self.assertFalse(result["success"])
        self.assertFalse(result["post_deleted"])
        self.assertEqual(result["message"], "You had no reaction on this post.")
        self.assertFalse(line.liked_by_account)
        self.assertNotEqual(line.state, "deleted")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_unlike_post_error_keeps_the_reaction(self, mock_request):
        """An error that names nothing must not redraw the entry."""
        line = self.SocialPostAccountLinkedin
        line.liked_by_account = True
        failed = MagicMock()
        failed.status_code = 500
        failed.text = '{"message": "Internal error occurred."}'
        mock_request.return_value = failed
        result = line.action_unlike_post(author_urn="urn:li:person:abc")
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Internal error occurred.")
        self.assertTrue(result["liked"])
        self.assertTrue(line.liked_by_account)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_unlike_comment(self, mock_request):
        """A comment reaction is withdrawn by the same pair, without a field."""
        line = self.SocialPostAccountLinkedin
        author_urn = "urn:li:person:abc"
        comment_ref = "urn:li:comment:(urn:li:activity:6666,120381273128)"
        deleted = MagicMock()
        deleted.status_code = 204
        mock_request.return_value = deleted
        result = line.action_unlike_comment(comment_ref, author_urn)
        self.assertTrue(result["success"])
        self.assertFalse(result["liked"])
        self.assertEqual(mock_request.call_args.kwargs["method"], "DELETE")
        self.assertEqual(
            mock_request.call_args.kwargs["endpoint"],
            f"/reactions/(actor:{quote(author_urn, safe='')},"
            f"entity:{quote(comment_ref, safe='')})",
        )

        reaction_gone = MagicMock()
        reaction_gone.status_code = 404
        post_alive = MagicMock()
        post_alive.status_code = 200
        mock_request.side_effect = [reaction_gone, post_alive]
        result = line.action_unlike_comment(comment_ref, author_urn)
        self.assertFalse(result["success"])
        self.assertFalse(result["post_deleted"])
        self.assertEqual(result["message"], "You had no reaction on this comment.")
        self.assertFalse(result["liked"])

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_react_comment_unknown_error_says_nothing(self, mock_request):
        """An error that names nothing answers ``None``, not a reaction."""
        line = self.SocialPostAccountLinkedin
        failed = MagicMock()
        failed.status_code = 500
        failed.text = '{"message": "Internal error occurred."}'
        mock_request.return_value = failed
        comment_ref = "urn:li:comment:(urn:li:activity:6666,120381273128)"
        result = line.action_like_comment(comment_ref, "urn:li:person:abc")
        self.assertIsNone(result["liked"])
        result = line.action_unlike_comment(comment_ref, "urn:li:person:abc")
        self.assertIsNone(result["liked"])

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_like_comment(self, mock_request):
        """The Reactions API takes the comment URN in ``root``."""
        author_urn = "urn:li:person:abc"
        comment_ref = "urn:li:comment:(urn:li:activity:6666,120381273128)"
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.action_like_comment(
            comment_ref, author_urn
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "")
        json_data = mock_request.call_args.kwargs["json_data"]
        self.assertEqual(json_data["root"], comment_ref)
        self.assertEqual(json_data["reactionType"], "LIKE")
        self.assertEqual(
            mock_request.call_args.kwargs["params_values"], {"actor": author_urn}
        )

        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.action_like_comment(
            comment_ref, author_urn
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "You have already reacted to this comment.")

        reaction_gone = MagicMock()
        reaction_gone.status_code = 404
        post_alive = MagicMock()
        post_alive.status_code = 200
        mock_request.side_effect = [reaction_gone, post_alive]
        result = self.SocialPostAccountLinkedin.action_like_comment(
            comment_ref, author_urn
        )
        self.assertFalse(result["success"])
        self.assertFalse(result["post_deleted"])
        self.assertEqual(
            result["message"], "The comment does not exist or has been deleted."
        )
        self.assertNotEqual(
            self.SocialPostAccountLinkedin.state,
            "deleted",
            msg="A comment gone on its own leaves the publication alone.",
        )
        mock_request.side_effect = None

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = '{"message": "Internal error occurred."}'
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.action_like_comment(
            comment_ref, author_urn
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Internal error occurred.")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_like_post_not_found_but_alive(self, mock_request):
        """A ``404`` of the reaction alone does not mark the post deleted."""
        reaction_gone = MagicMock()
        reaction_gone.status_code = 404
        reaction_gone.text = '{"message": "Internal error occurred."}'
        post_alive = MagicMock()
        post_alive.status_code = 200
        mock_request.side_effect = [reaction_gone, post_alive]
        result = self.SocialPostAccountLinkedin.action_like_post(
            author_urn="urn:li:person:abc"
        )
        self.assertFalse(result["success"])
        self.assertFalse(result["post_deleted"])
        self.assertEqual(result["message"], "Internal error occurred.")
        self.assertNotEqual(self.SocialPostAccountLinkedin.state, "deleted")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_like_comment_when_the_post_is_gone(self, mock_request):
        """A comment answering ``404`` because its publication is gone."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.action_like_comment(
            "urn:li:comment:(urn:li:activity:6666,120381273128)",
            "urn:li:person:abc",
        )
        self.assertFalse(result["success"])
        self.assertTrue(result["post_deleted"])
        self.assertEqual(
            result["message"], "The post does not exist or has been deleted."
        )
        self.assertEqual(self.SocialPostAccountLinkedin.state, "deleted")

    def test_action_like_comment_without_reference(self):
        """A comment LinkedIn answered without its URN cannot be reacted to."""
        with patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin")) as mock_request:
            result = self.SocialPostAccountLinkedin.action_like_comment(
                None, "urn:li:person:abc"
            )
            mock_request.assert_not_called()
        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"], "The comment cannot be recommended on LinkedIn."
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_builds_the_comment_urn(self, mock_request):
        """socialActions does not always answer ``commentUrn``, so it is built."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": "120381273128",
                    "object": "urn:li:activity:6666",
                    "message": {"text": "Great post!"},
                    "content": [],
                }
            ]
        }
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comments()
        self.assertEqual(
            result["data"][0]["remote_ref"],
            "urn:li:comment:(urn:li:activity:6666,120381273128)",
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_falls_back_to_the_publication_thread(self, mock_request):
        """Without ``object``, the thread is the publication itself."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [{"id": "1", "message": {"text": "Hi"}, "content": []}]
        }
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comments()
        self.assertEqual(
            result["data"][0]["remote_ref"],
            f"urn:li:comment:({self.SocialPostAccountLinkedin.remote_ref},1)",
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_prefers_the_urn_linkedin_sends(self, mock_request):
        """``$URN`` is the reference of LinkedIn itself, so it wins."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {
                    "$URN": "urn:li:comment:(urn:li:activity:6666,999)",
                    "id": "120381273128",
                    "object": "urn:li:activity:6666",
                    "message": {"text": "Great post!"},
                    "content": [],
                }
            ]
        }
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comments()
        self.assertEqual(
            result["data"][0]["remote_ref"],
            "urn:li:comment:(urn:li:activity:6666,999)",
        )
        self.assertFalse(
            result["data"][0]["parent_ref"],
            msg="A comment of the post hangs from no other comment.",
        )
        self.assertIsNone(
            result["data"][0]["reply_count"],
            msg="LinkedIn does not say how many replies a comment has "
            "until they are asked for.",
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_reads_the_parent_from_parent_comment(self, mock_request):
        """``parentComment`` is what says which comment a reply answers."""
        comment_ref = "urn:li:comment:(urn:li:activity:6666,120381273128)"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {
                    "$URN": "urn:li:comment:(urn:li:activity:6666,999)",
                    "id": "999",
                    "object": "urn:li:activity:6666",
                    "parentComment": comment_ref,
                    "message": {"text": "A reply"},
                    "content": [],
                }
            ]
        }
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comments()
        self.assertEqual(result["data"][0]["parent_ref"], comment_ref)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_invents_no_parent_from_the_thread(self, mock_request):
        """The thread of a comment is not the comment it answers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {
                    "$URN": "urn:li:comment:(urn:li:ugcPost:6666,999)",
                    "id": "999",
                    "object": "urn:li:ugcPost:6666",
                    "message": {"text": "Great post!"},
                    "content": [],
                }
            ]
        }
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comments()
        self.assertFalse(result["data"][0]["parent_ref"])

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comment_replies_success(self, mock_request):
        """The replies are read from the social action of the comment."""
        comment_ref = "urn:li:comment:(urn:li:activity:6666,120381273128)"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "paging": {"start": 0, "count": 10, "total": 2},
            "elements": [
                {
                    "$URN": "urn:li:comment:(urn:li:activity:6666,120381273129)",
                    "id": "120381273129",
                    "object": "urn:li:activity:6666",
                    "parentComment": comment_ref,
                    "message": {"text": "First reply"},
                    "content": [],
                },
                {
                    "$URN": "urn:li:comment:(urn:li:activity:6666,120381273130)",
                    "id": "120381273130",
                    "object": "urn:li:activity:6666",
                    "parentComment": comment_ref,
                    "message": {"text": "Second reply"},
                    "content": [],
                },
            ],
        }
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comment_replies(comment_ref)
        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(
            result["count"], 2, msg="The counter is the ``total`` of the paging."
        )
        self.assertEqual(
            mock_request.call_args_list[0].kwargs["endpoint"],
            f"/socialActions/{quote(comment_ref)}/comments",
        )
        self.assertEqual(
            mock_request.call_args_list[1].kwargs["endpoint"],
            "/reactions",
            msg="Which replies the account reacted to costs one call, not one "
            "per reply.",
        )
        self.assertFalse(
            result["data"][0]["liked"],
            msg="LinkedIn answered no reaction of this account.",
        )
        self.assertEqual(
            result["data"][0]["parent_ref"],
            comment_ref,
            msg="A reply hangs from the comment it answers.",
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comment_replies_without_replies(self, mock_request):
        """A comment nobody answered is answered with an empty page."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "paging": {"start": 0, "count": 10, "links": [], "total": 0},
            "elements": [],
        }
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comment_replies(
            "urn:li:comment:(urn:li:activity:6666,120381273128)"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], [])
        self.assertEqual(result["count"], 0)

    @mute_logger(LOGGER_POST_ACCOUNT_SYNC_LINKEDIN)
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comment_replies_failed(self, mock_request):
        """A refusal of LinkedIn is reported without breaking the dialog."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comment_replies(
            "urn:li:comment:(urn:li:activity:6666,120381273128)"
        )
        self.assertFalse(result["success"])
        self.assertIn("replies could not be read from LinkedIn", result["message"])
        self.assertEqual(result["data"], [])
        self.assertEqual(result["count"], 0)

    def test_get_comment_replies_calls_super(self):
        with patch(PATCH_SYNC_POST_ACCOUNT.format("get_comment_replies")) as mock_super:
            self.SocialPostAccount.get_comment_replies("urn:li:comment:(x,1)")
            mock_super.assert_called_once()

    def test_get_comment_replies_answers_another_media_verbatim(self):
        """Delegating is not enough: super() answers, and that is the answer.

        This connector is the only one implementing the hook, so nothing else
        writes to this path and a rewritten answer would go unnoticed.
        """
        answer = {
            "success": False,
            "message": "Only the media of the publication answers.",
            "data": [{"id": "foreign"}],
            "count": 1,
        }
        with patch(
            PATCH_SYNC_POST_ACCOUNT.format("get_comment_replies"), return_value=answer
        ):
            self.assertEqual(
                self.SocialPostAccount.get_comment_replies("urn:li:comment:(x,1)"),
                answer,
            )

    def test_linkedin_comment_urn_without_identifier(self):
        self.assertEqual(self.SocialPostAccountLinkedin._linkedin_comment_urn({}), "")

    def test_action_like_comment_calls_super(self):
        with patch(PATCH_SYNC_POST_ACCOUNT.format("action_like_comment")) as mock_super:
            self.SocialPostAccount.action_like_comment()
            mock_super.assert_called_once()

    def test_action_like_post_failed(self):
        with patch(
            PATCH_SYNC_POST_ACCOUNT.format("action_like_post")
        ) as mock_like_super:
            self.SocialPostAccount.action_like_post()
            mock_like_super.assert_called_once()

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": "comment1",
                    "commentUrn": "urn:li:comment:(urn:li:activity:1,comment1)",
                    "message": {"text": "Great post!"},
                    "lastModified": {
                        "actor": "urn:li:person:actor1",
                        "time": 1609459200000,
                    },
                    "content": [{"url": "http://example.com/image1.jpg"}],
                }
            ]
        }
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comments()
        data = result["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "comment1")
        self.assertEqual(
            data[0]["remote_ref"], "urn:li:comment:(urn:li:activity:1,comment1)"
        )
        self.assertEqual(data[0]["text"], "Great post!")
        self.assertEqual(
            data[0]["actor"],
            "LinkedIn member",
            msg="The client is answered a name to draw, and LinkedIn does "
            "not let a member be named.",
        )
        self.assertEqual(data[0]["images_url"], ["http://example.com/image1.jpg"])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"elements": []}
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comments()
        self.assertEqual(result["data"], [])

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_without_last_modified(self, mock_request):
        """LinkedIn may answer a comment without its modification data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": "comment1",
                    "message": {"text": "Great post!"},
                    "content": [],
                }
            ]
        }
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comments()
        self.assertTrue(result["success"])
        self.assertEqual(
            result["data"][0]["actor"],
            "LinkedIn page",
            msg="An unstamped comment says nothing about who wrote it, and "
            "a neutral label is what is drawn instead of the account.",
        )

    @mute_logger(LOGGER_POST_ACCOUNT_SYNC_LINKEDIN)
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_failed(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.get_comments()
        self.assertFalse(result["success"])
        self.assertIn("comments could not be read from LinkedIn", result["message"])

    def test_get_comments_answers_another_media_verbatim(self):
        """The comments of another social media come back untouched.

        Every existing check of the hook drives the LinkedIn path, so the
        guard that hands the answer of another network over is asserted here:
        ``success`` and the message explaining a failure of its own travel
        back whole, not only the comments in ``data``.
        """
        answer = {
            "success": False,
            "message": "Only the media of the publication answers.",
            "data": [{"id": "foreign"}],
        }
        with patch(PATCH_SYNC_POST_ACCOUNT.format("get_comments"), return_value=answer):
            self.assertEqual(self.SocialPostAccount.get_comments(), answer)

    @mute_logger(LOGGER_POST_ACCOUNT_SYNC_LINKEDIN)
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_linkedin_prepare_images_for_post"))
    def test_create_linkedin_comment_success(self, mock_prepare_images, mock_request):
        mock_prepare_images.return_value = [{"media": "asset_123"}]
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"message": "Comment created successfully"}
        mock_request.return_value = mock_response
        post_data = {
            "body": "Great post!",
            "attachment_ids": [1],
        }
        result = self.SocialPostAccountLinkedin._create_linkedin_comment(post_data)
        self.assertEqual(result["success"], True)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"message": "Comment created successfully"}
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin._create_linkedin_comment(post_data)
        self.assertEqual(result["success"], True)

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_request.return_value = mock_response
        post_data.update({"attachment_ids": []})
        result = self.SocialPostAccountLinkedin._create_linkedin_comment(post_data)
        self.assertFalse(result["success"])
        self.assertIn("comment could not be published on LinkedIn", result["message"])

    @mute_logger(LOGGER_POST_ACCOUNT_SYNC_LINKEDIN)
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_create_linkedin_comment_post_gone(self, mock_request):
        """A comment refused with ``404`` marks the publication as deleted."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin._create_linkedin_comment(
            {"body": "A comment"}
        )
        self.assertFalse(result["success"])
        self.assertTrue(result["post_deleted"])
        self.assertEqual(
            result["message"], "The post does not exist or has been deleted."
        )
        self.assertEqual(self.SocialPostAccountLinkedin.state, "deleted")

    @mute_logger(LOGGER_POST_ACCOUNT_SYNC_LINKEDIN)
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_create_linkedin_comment_not_found_but_alive(self, mock_request):
        """A ``404`` with the publication still online is reported as an error."""
        comment_gone = MagicMock()
        comment_gone.status_code = 404
        comment_gone.text = '{"message": "Internal error occurred."}'
        post_alive = MagicMock()
        post_alive.status_code = 200
        mock_request.side_effect = [comment_gone, post_alive]
        result = self.SocialPostAccountLinkedin._create_linkedin_comment(
            {"body": "A comment"}
        )
        self.assertFalse(result["success"])
        self.assertFalse(result["post_deleted"])
        self.assertIn("comment could not be published on LinkedIn", result["message"])
        self.assertNotEqual(self.SocialPostAccountLinkedin.state, "deleted")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_create_linkedin_comment_replies_to_a_comment(self, mock_request):
        """With a parent, the reply names it in ``parentComment``."""
        comment_ref = "urn:li:comment:(urn:li:activity:6666,120381273128)"
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin._create_linkedin_comment(
            {"body": "A reply", "social_parent_ref": comment_ref}
        )
        self.assertTrue(result["success"])
        call_kwargs = mock_request.call_args.kwargs
        self.assertEqual(
            call_kwargs["endpoint"],
            f"/socialActions/{quote(comment_ref)}/comments",
        )
        json_data = call_kwargs["json_data"]
        self.assertEqual(
            json_data["object"],
            self.SocialPostAccountLinkedin.remote_ref,
            msg="``object`` is the publication the thread lives on, also for "
            "a reply.",
        )
        self.assertEqual(
            json_data["parentComment"],
            comment_ref,
            msg="``parentComment`` is the only field that nests the reply.",
        )
        self.assertEqual(json_data["actor"], self.SocialAccountLinkedin.remote_ref)
        self.assertEqual(json_data["message"], {"text": "A reply"})

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_create_linkedin_comment_without_parent(self, mock_request):
        """Without a parent, the comment is published where it always was."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin._create_linkedin_comment(
            {"body": "A comment"}
        )
        self.assertTrue(result["success"])
        call_kwargs = mock_request.call_args.kwargs
        post_ref = self.SocialPostAccountLinkedin.remote_ref
        self.assertEqual(
            call_kwargs["endpoint"], f"/socialActions/{quote(post_ref)}/comments"
        )
        self.assertEqual(call_kwargs["json_data"]["object"], post_ref)
        self.assertNotIn(
            "parentComment",
            call_kwargs["json_data"],
            msg="A first-level comment answers no other comment.",
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_create_linkedin_comment_answers_the_created_comment(self, mock_request):
        """The comment LinkedIn creates travels back already shaped."""
        comment_ref = "urn:li:comment:(urn:li:activity:6666,120381273128)"
        parent_ref = "urn:li:comment:(urn:li:activity:6666,120381273000)"
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "120381273128",
            "$URN": comment_ref,
            "object": "urn:li:activity:6666",
            "parentComment": parent_ref,
            "message": {"text": "A reply"},
            "created": {"actor": "urn:li:person:_prFA0zDNN", "time": 1756000000000},
            "content": [],
        }
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin._create_linkedin_comment(
            {"body": "A reply", "social_parent_ref": parent_ref}
        )
        self.assertTrue(result["success"])
        self.assertEqual(
            mock_request.call_count,
            1,
            msg="The created comment comes from the answer of the creation, "
            "so the thread is not read again.",
        )
        comment = result["comment"]
        self.assertEqual(comment["remote_ref"], comment_ref)
        self.assertEqual(comment["parent_ref"], parent_ref)
        self.assertEqual(comment["text"], "A reply")
        self.assertEqual(
            comment["actor"],
            "LinkedIn member",
            msg="A comment just created is stamped in ``created``, not in "
            "``lastModified``, and that stamp is what names its author.",
        )
        self.assertIsInstance(
            comment["published_time"],
            str,
            msg="The epoch LinkedIn stamps the comment with is turned into "
            "the sentence the client draws, not handed over as a date.",
        )

    @mute_logger(LOGGER_POST_ACCOUNT_SYNC_LINKEDIN)
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_create_linkedin_comment_unshapeable_answer(self, mock_request):
        """An answer that does not name the comment answers no comment."""
        for body in ({"message": "Created"}, ValueError, ["not", "a", "comment"]):
            mock_response = MagicMock()
            mock_response.status_code = 201
            if body is ValueError:
                mock_response.json.side_effect = ValueError
            else:
                mock_response.json.return_value = body
            mock_request.return_value = mock_response
            result = self.SocialPostAccountLinkedin._create_linkedin_comment(
                {"body": "A comment"}
            )
            self.assertTrue(result["success"])
            self.assertNotIn(
                "comment",
                result,
                msg="Without the key the client rereads the thread, which is "
                "the fallback and not a failure.",
            )

    def test_linkedin_comment_stamp_prefers_last_modified(self):
        """A comment read from the thread is stamped in ``lastModified``."""
        element = {
            "lastModified": {"actor": "urn:li:person:edited", "time": 2},
            "created": {"actor": "urn:li:person:wrote", "time": 1},
        }
        self.assertEqual(
            self.SocialPostAccountLinkedin._linkedin_comment_stamp(element)["actor"],
            "urn:li:person:edited",
        )
        self.assertEqual(
            self.SocialPostAccountLinkedin._linkedin_comment_stamp({}),
            {},
            msg="An element with neither stamp answers nothing to read.",
        )

    def test_linkedin_comment_time_reads_the_epoch_in_utc(self):
        """The epoch of LinkedIn is converted here, in UTC, into a moment."""
        element = {"created": {"actor": "urn:li:person:wrote", "time": 1756000000000}}
        self.assertEqual(
            self.SocialPostAccountLinkedin._linkedin_comment_time(element),
            datetime(2025, 8, 24, 1, 46, 40),
            msg="The moment comes back naive and read as UTC.",
        )

    def test_linkedin_comment_time_without_a_stamp(self):
        """An element LinkedIn stamped with nothing is not dated at the epoch."""
        self.assertFalse(self.SocialPostAccountLinkedin._linkedin_comment_time({}))

    @freeze_time("2025-08-31 01:46:40")
    def test_linkedin_comment_values_say_how_long_ago(self):
        """What the client draws is the sentence, whatever LinkedIn answered."""
        element = {
            "id": "120381273128",
            "$URN": "urn:li:comment:(urn:li:activity:6666,120381273128)",
            "message": {"text": "A comment"},
            "created": {"actor": "urn:li:person:wrote", "time": 1756000000000},
            "content": [],
        }
        self.assertEqual(
            self.SocialPostAccountLinkedin._linkedin_comment_values(element)[
                "published_time"
            ],
            "1 week ago",
            msg="The sentence is the one babel builds for the distance, and "
            "it counts in the largest unit that fits.",
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_delete_comment_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response
        comment_id = "123456"
        result = self.SocialPostAccountLinkedin.delete_comment(comment_id)
        self.assertEqual(result["success"], True)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal Server Error"}
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.delete_comment(comment_id)
        self.assertEqual(result["success"], False)

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}
        mock_request.return_value = mock_response
        result = self.SocialPostAccountLinkedin.delete_comment(comment_id)
        self.assertEqual(result["success"], False)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_delete_comment_acts_as_the_account(self, mock_request):
        """The actor of the deletion is the account, never what is sent in."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response
        self.SocialPostAccountLinkedin.delete_comment("123456")
        call_kwargs = mock_request.call_args.kwargs
        self.assertEqual(
            call_kwargs["params_values"]["actor"],
            self.SocialAccountLinkedin.remote_ref,
        )

    def test_delete_comment_takes_no_actor_from_the_caller(self):
        """The signature offers no way of choosing whom the deletion acts as."""
        with self.assertRaises(TypeError):
            self.SocialPostAccountLinkedin.delete_comment(
                "123456", "urn:li:person:somebody-else"
            )

    @patch(PATCH_SYNC_POST_ACCOUNT_LINKEDIN.format("_create_linkedin_comment"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_create_comment(self, mock_request_linkedin, mock_create_linkedin_comment):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_request_linkedin.return_value = mock_response
        result = self.SocialPostAccountLinkedin.create_comment(
            {"body": "Test comment", "attachment_ids": [1]}
        )
        self.assertTrue(result["success"])
        mock_create_linkedin_comment.assert_called_once()

    def test_get_comments_of_a_publication_without_reference(self):
        """A publication LinkedIn never named has no thread to read."""
        with patch.object(
            type(self.SocialAccountLinkedin), "_request_linkedin"
        ) as mock_request:
            result = self.SocialPostAccountReadyLinkedin.get_comments()
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], [])
        self.assertFalse(
            mock_request.called,
            msg="Without a URN there is nothing to ask LinkedIn about.",
        )

    @patch(PATCH_SYNC_ACCOUNT_LINKEDIN.format("_get_reactions"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_claims_no_reaction_when_linkedin_is_silent(
        self, mock_request, mock_reactions
    ):
        """Not knowing leaves the entry drawn as a reaction still to be made."""
        mock_reactions.return_value = None
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {
                    "id": "comment1",
                    "commentUrn": "urn:li:comment:(urn:li:activity:1,comment1)",
                    "message": {"text": "Great post!"},
                    "lastModified": {
                        "actor": "urn:li:person:actor1",
                        "time": 1609459200000,
                    },
                    "content": [],
                }
            ]
        }
        mock_request.return_value = mock_response
        comment = self.SocialPostAccountLinkedin.get_comments()["data"][0]
        self.assertFalse(comment["liked"])

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_unlike_post_when_the_post_is_gone(self, mock_request):
        """The pair is missing because the publication itself is."""
        line = self.SocialPostAccountLinkedin
        line.liked_by_account = True
        gone = MagicMock()
        gone.status_code = 404
        mock_request.return_value = gone
        result = line.action_unlike_post(author_urn="urn:li:person:abc")
        self.assertFalse(result["success"])
        self.assertTrue(result["post_deleted"])
        self.assertEqual(
            result["message"], "The post does not exist or has been deleted."
        )
        self.assertEqual(line.state, "deleted")
        self.assertTrue(
            result["liked"],
            msg="Nothing says the reaction was withdrawn, only that the "
            "publication is gone.",
        )

    def test_action_unlike_post_answers_another_media_verbatim(self):
        """The withdrawal of another network comes back untouched."""
        answer = {
            "success": False,
            "message": "Only the media of the publication answers.",
            "post_deleted": False,
            "liked": True,
        }
        with patch(
            PATCH_SYNC_POST_ACCOUNT.format("action_unlike_post"), return_value=answer
        ):
            self.assertEqual(self.SocialPostAccount.action_unlike_post(), answer)

    def test_action_unlike_comment_without_reference(self):
        """A comment LinkedIn answered without its URN cannot be addressed."""
        with patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin")) as mock_request:
            result = self.SocialPostAccountLinkedin.action_unlike_comment(
                None, "urn:li:person:abc"
            )
            mock_request.assert_not_called()
        self.assertFalse(result["success"])
        self.assertIsNone(result["liked"])
        self.assertEqual(
            result["message"], "The comment cannot be recommended on LinkedIn."
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_unlike_comment_when_the_post_is_gone(self, mock_request):
        """A comment whose publication is gone marks the publication."""
        line = self.SocialPostAccountLinkedin
        gone = MagicMock()
        gone.status_code = 404
        mock_request.return_value = gone
        result = line.action_unlike_comment(
            "urn:li:comment:(urn:li:activity:6666,120381273128)",
            "urn:li:person:abc",
        )
        self.assertFalse(result["success"])
        self.assertTrue(result["post_deleted"])
        self.assertEqual(
            result["message"], "The post does not exist or has been deleted."
        )
        self.assertEqual(line.state, "deleted")

    def test_action_unlike_comment_answers_another_media_verbatim(self):
        """The withdrawal on a comment of another network is not rewritten."""
        answer = {
            "success": True,
            "message": "",
            "post_deleted": False,
            "liked": False,
        }
        with patch(
            PATCH_SYNC_POST_ACCOUNT.format("action_unlike_comment"), return_value=answer
        ):
            self.assertEqual(
                self.SocialPostAccount.action_unlike_comment("comment-1"), answer
            )

    def test_create_linkedin_comment_of_another_media_calls_nothing(self):
        """The LinkedIn creation is not the one another network publishes by."""
        with patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin")) as mock_request:
            result = self.SocialPostAccount._create_linkedin_comment(
                {"body": "Test comment"}
            )
            mock_request.assert_not_called()
        self.assertEqual(result, {"success": True, "post_deleted": False})

    def test_created_comment_without_a_reference_is_not_shaped(self):
        """A comment the client cannot react to is left to a reread.

        The URN is built from the thread the publication is on, so a
        publication LinkedIn never named cannot carry one.
        """
        response = MagicMock()
        response.json.return_value = {"id": "120381273128"}
        self.assertEqual(
            self.SocialPostAccountReadyLinkedin._linkedin_created_comment(response), {}
        )

    def test_create_comment_of_another_media_is_delegated(self):
        """Publishing a comment on another network is its connector's."""
        answer = {"success": True, "post_deleted": False, "comment": {"id": "foreign"}}
        with patch(
            PATCH_SYNC_POST_ACCOUNT.format("create_comment"), return_value=answer
        ) as mock_super:
            self.assertEqual(
                self.SocialPostAccount.create_comment({"body": "Test comment"}), answer
            )
        mock_super.assert_called_once()

    def test_delete_comment_of_another_media_is_delegated(self):
        """Deleting a comment of another network is its connector's."""
        answer = {"success": True}
        with patch(
            PATCH_SYNC_POST_ACCOUNT.format("delete_comment"), return_value=answer
        ) as mock_super:
            self.assertEqual(self.SocialPostAccount.delete_comment("123456"), answer)
        mock_super.assert_called_once()
