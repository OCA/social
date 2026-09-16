# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from ast import literal_eval
from datetime import datetime
from unittest.mock import MagicMock, patch

from lxml import etree

from odoo.tools import mute_logger

from odoo.addons.social_media_sync.tests.test_social_sync_common import (
    PATCH_SYNC_POST_ACCOUNT,
)

from ..social_x_sync_utils import _COMMENTS_MAX_PAGES_X, _SEARCH_MAX_RESULTS_X
from .test_sync_x_common import LOGGER_POST_ACCOUNT_X_SYNC, TestSocialSyncCommonX


class TestSocialSyncPostAccountX(TestSocialSyncCommonX):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_response_errors = ["Error 1", "Error 2"]
        cls.post_data = {
            "body": "Test Comment",
            "attachment_ids": [1],
        }

    def create_test_comment(self):
        return self.SocialPostAccountX.create_x_comment(self.post_data)

    def test_create_comment(self):
        with patch.object(
            type(self.SocialPostAccountX), "create_x_comment"
        ) as mock_create_comment:
            self.SocialPostAccountX.create_comment(self.post_data)
            mock_create_comment.assert_called_once()

    def test_create_comment_super(self):
        with patch(
            PATCH_SYNC_POST_ACCOUNT.format("create_comment")
        ) as mock_create_comment:
            self.SocialPostAccount.create_comment(self.post_data)
            mock_create_comment.assert_called_once()

    def test_create_comment_answers_another_media_verbatim(self):
        """Delegating is not enough: what the chain answered comes back whole.

        The comment of another social media is created by its own connector,
        and this one neither writes the tweet nor touches the answer.
        """
        answer = {
            "success": False,
            "message": "Only the media of the publication answers.",
            "post_deleted": True,
        }
        with (
            patch(
                PATCH_SYNC_POST_ACCOUNT.format("create_comment"), return_value=answer
            ),
            patch.object(
                type(self.SocialPostAccount), "create_x_comment"
            ) as mock_create_x_comment,
        ):
            self.assertEqual(
                self.SocialPostAccount.create_comment(self.post_data), answer
            )
            mock_create_x_comment.assert_not_called()

    def test_create_x_comment(self):
        media_refs = {"1": "media_1"}
        fake_client = MagicMock()
        fake_client.create_tweet.return_value = True
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with (
            mock_valid_time_request,
            mock_get_client_api as mock_client_api,
            patch.object(
                type(self.SocialAccountX),
                "_prepare_medias_for_tweet",
                return_value=media_refs,
            ) as mock_medias_for_tweet,
        ):
            res = self.create_test_comment()
            mock_medias_for_tweet.assert_called_once()
            mock_client_api.assert_called_once()
        self.assertEqual(
            fake_client.create_tweet.call_args.kwargs["media_ids"],
            list(media_refs.values()),
            msg="X is given the references of the medias, not the mapping.",
        )
        self.assertTrue(res["success"])

        with (
            mock_valid_time_request,
            mock_get_client_api as mock_client_api,
        ):
            res_without_attach = self.SocialPostAccountX.create_x_comment(
                {
                    "body": self.test_message,
                }
            )
            mock_client_api.assert_called_once()
        self.assertTrue(res_without_attach["success"])

    def test_create_x_comment_replies_to_a_comment(self):
        """With a parent, the reply answers that tweet, not the post."""
        comment_ref = "1234567890"
        fake_client = MagicMock()
        fake_client.create_tweet.return_value = True
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with (
            mock_valid_time_request,
            mock_get_client_api,
            patch.object(
                type(self.SocialAccountX),
                "_prepare_medias_for_tweet",
                return_value={"1": "media_1"},
            ),
        ):
            self.SocialPostAccountX.create_x_comment(
                {
                    "body": self.test_message,
                    "attachment_ids": [1],
                    "social_parent_ref": comment_ref,
                }
            )
        self.assertEqual(
            fake_client.create_tweet.call_args.kwargs["in_reply_to_tweet_id"],
            comment_ref,
            msg="The branch with attachments answers the comment.",
        )

        with mock_valid_time_request, mock_get_client_api:
            self.SocialPostAccountX.create_x_comment(
                {"body": self.test_message, "social_parent_ref": comment_ref}
            )
        self.assertEqual(
            fake_client.create_tweet.call_args.kwargs["in_reply_to_tweet_id"],
            comment_ref,
            msg="The branch without attachments answers the comment too.",
        )

    def test_create_x_comment_without_parent(self):
        """Without a parent, the comment answers the publication."""
        fake_client = MagicMock()
        fake_client.create_tweet.return_value = True
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_valid_time_request, mock_get_client_api:
            self.SocialPostAccountX.create_x_comment({"body": self.test_message})
        self.assertEqual(
            fake_client.create_tweet.call_args.kwargs["in_reply_to_tweet_id"],
            self.SocialPostAccountX.remote_ref,
        )

    def test_create_x_comment_answers_the_created_comment(self):
        """The tweet X creates travels back shaped as a comment."""
        comment_ref = "1234567890"
        fake_client = MagicMock()
        fake_client.create_tweet.return_value = MagicMock(
            data={"id": 9876543210, "text": "A reply"}
        )
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with (
            mock_valid_time_request,
            mock_get_client_api,
            patch.object(
                type(self.SocialAccountX),
                "_prepare_medias_for_tweet",
                return_value={"1": "media_1"},
            ),
        ):
            result = self.SocialPostAccountX.create_x_comment(
                {
                    "body": self.test_message,
                    "attachment_ids": [1],
                    "social_parent_ref": comment_ref,
                }
            )
        self.assertTrue(result["success"])
        comment = result["comment"]
        self.assertEqual(
            comment["remote_ref"],
            "9876543210",
            msg="On X a comment is a tweet, so the identifier names it.",
        )
        self.assertEqual(comment["parent_ref"], comment_ref)
        self.assertEqual(comment["text"], "A reply")
        self.assertEqual(comment["actor"], self.SocialAccountX.name)
        self.assertEqual(comment["reply_count"], 0)
        self.assertEqual(
            comment["images_url"],
            ["/web/image/1"],
            msg="The images went up from Odoo, so they are drawn from Odoo "
            "instead of asking X for them.",
        )
        self.assertIsInstance(
            comment["published_time"],
            str,
            msg="The client draws the moment as it arrives, so what travels "
            "is the sentence saying how long ago it was and never a date.",
        )

    def test_create_x_comment_first_level_has_no_parent(self):
        """A comment on the publication hangs from nothing."""
        fake_client = MagicMock()
        fake_client.create_tweet.return_value = MagicMock(
            data={"id": "9876543210", "text": "A comment"}
        )
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_valid_time_request, mock_get_client_api:
            result = self.SocialPostAccountX.create_x_comment(
                {"body": self.test_message}
            )
        self.assertFalse(result["comment"]["parent_ref"])
        self.assertEqual(result["comment"]["images_url"], [])

    def test_create_x_comment_unshapeable_answer(self):
        """A creation that names no tweet answers no comment."""
        for answer in (True, MagicMock(data={}), MagicMock(data=None)):
            fake_client = MagicMock()
            fake_client.create_tweet.return_value = answer
            (
                mock_get_client_api,
                mock_valid_time_request,
            ) = self.get_patch_exceptions_x(fake_client)
            with mock_valid_time_request, mock_get_client_api:
                result = self.SocialPostAccountX.create_x_comment(
                    {"body": self.test_message}
                )
            self.assertTrue(result["success"])
            self.assertNotIn(
                "comment",
                result,
                msg="Without the key the client rereads the thread, which is "
                "the fallback and not a failure.",
            )

    def test_get_comments_nests_the_replies_of_the_thread(self):
        """The conversation arrives whole, so the replies are placed here."""
        now = datetime.now()
        fake_user = MagicMock()
        fake_user.id = "author_1"
        fake_user.profile_image_url = None
        comment = MagicMock()
        comment.id = "100"
        comment.text = "A comment of the post"
        comment.author_id = "author_1"
        comment.created_at = now
        comment.attachments = None
        comment.referenced_tweets = [
            MagicMock(type="replied_to", id=self.SocialPostAccountX.remote_ref)
        ]
        reply = MagicMock()
        reply.id = "200"
        reply.text = "A reply to that comment"
        reply.author_id = "author_1"
        reply.created_at = now
        reply.attachments = None
        reply.referenced_tweets = [MagicMock(type="replied_to", id="100")]
        fake_response = MagicMock()
        fake_response.data = [comment, reply]
        fake_response.includes = {"users": [fake_user]}
        fake_response.meta = {}
        fake_client = MagicMock()
        fake_client.search_recent_tweets.return_value = fake_response
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            comments = self.SocialPostAccountX.get_comments()
        by_ref = {comment["remote_ref"]: comment for comment in comments["data"]}
        self.assertFalse(
            by_ref["100"]["parent_ref"],
            msg="A tweet answering the post hangs from no comment.",
        )
        self.assertEqual(
            by_ref["200"]["parent_ref"],
            "100",
            msg="A tweet answering another tweet of the thread hangs from it.",
        )
        self.assertEqual(by_ref["100"]["reply_count"], 1)
        self.assertEqual(by_ref["200"]["reply_count"], 0)
        self.assertIsInstance(
            by_ref["100"]["published_time"],
            str,
            msg="The moment X stamps the tweet with is turned into the "
            "sentence the client draws, not handed over as a date.",
        )

    def _fake_author_x(self, ref="author_1"):
        author = MagicMock()
        author.id = ref
        author.name = "The author"
        author.profile_image_url = None
        return author

    def _fake_tweet_x(self, ref, parent_ref=None, author_ref="author_1"):
        """One tweet of the conversation as X answers it."""
        tweet = MagicMock()
        tweet.id = ref
        tweet.text = f"Tweet {ref}"
        tweet.author_id = author_ref
        tweet.created_at = datetime.now()
        tweet.attachments = None
        tweet.referenced_tweets = [
            MagicMock(
                type="replied_to",
                id=parent_ref or self.SocialPostAccountX.remote_ref,
            )
        ]
        return tweet

    def _fake_page_x(self, tweets, next_token=None):
        """One page of the recent search, with the token of the next one."""
        page = MagicMock()
        page.data = tweets
        page.includes = {"users": [self._fake_author_x()]}
        page.meta = {"next_token": next_token} if next_token else {}
        return page

    def test_get_comments_asks_for_a_whole_page(self):
        """A page of the conversation is asked for at the ceiling of X."""
        fake_response = MagicMock()
        fake_response.data = []
        fake_response.includes = {}
        fake_response.meta = {}
        fake_client = MagicMock()
        fake_client.search_recent_tweets.return_value = fake_response
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            self.SocialPostAccountX.get_comments()
        self.assertEqual(
            fake_client.search_recent_tweets.call_args.kwargs["max_results"],
            _SEARCH_MAX_RESULTS_X,
            msg="Without it X answers ten replies of its own accord, and a "
            "thread of eleven is read wrong.",
        )

    def test_get_comments_walks_the_pages_of_the_conversation(self):
        """A conversation longer than one page is read to its end."""
        first_page = [self._fake_tweet_x(f"1{index:03d}") for index in range(100)]
        second_page = [self._fake_tweet_x(f"2{index:03d}") for index in range(50)]
        fake_client = MagicMock()
        fake_client.search_recent_tweets.side_effect = [
            self._fake_page_x(first_page, next_token="page_2"),
            self._fake_page_x(second_page),
        ]
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            comments = self.SocialPostAccountX.get_comments()
        self.assertEqual(len(comments["data"]), 150)
        self.assertEqual(fake_client.search_recent_tweets.call_count, 2)
        self.assertEqual(
            fake_client.search_recent_tweets.call_args_list[1].kwargs["next_token"],
            "page_2",
            msg="The second page is asked for with the token the first one "
            "answered with.",
        )

    def test_get_comments_keeps_a_parent_read_on_another_page(self):
        """A reply finds its comment even when they came on different pages."""
        fake_client = MagicMock()
        fake_client.search_recent_tweets.side_effect = [
            self._fake_page_x([self._fake_tweet_x("100")], next_token="page_2"),
            self._fake_page_x([self._fake_tweet_x("200", parent_ref="100")]),
        ]
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            comments = self.SocialPostAccountX.get_comments()
        by_ref = {comment["remote_ref"]: comment for comment in comments["data"]}
        self.assertEqual(
            by_ref["200"]["parent_ref"],
            "100",
            msg="Read page by page the reply would hang from the "
            "publication, which is not where it was written.",
        )

    def test_get_comments_counts_the_replies_of_the_whole_conversation(self):
        """The count of a comment covers every page the walk brought."""
        replies = [
            self._fake_tweet_x(f"2{index:02d}", parent_ref="100") for index in range(12)
        ]
        fake_client = MagicMock()
        fake_client.search_recent_tweets.side_effect = [
            self._fake_page_x(
                [self._fake_tweet_x("100")] + replies[:5], next_token="page_2"
            ),
            self._fake_page_x(replies[5:]),
        ]
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            comments = self.SocialPostAccountX.get_comments()
        by_ref = {comment["remote_ref"]: comment for comment in comments["data"]}
        self.assertEqual(by_ref["100"]["reply_count"], 12)

    def test_get_comments_truncated_states_no_reply_count(self):
        """A walk stopped by the ceiling states no total it cannot back."""
        fake_client = MagicMock()
        fake_client.search_recent_tweets.side_effect = [
            self._fake_page_x(
                [self._fake_tweet_x(f"{page}00")], next_token=f"page_{page + 1}"
            )
            for page in range(_COMMENTS_MAX_PAGES_X)
        ]
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            comments = self.SocialPostAccountX.get_comments()
        self.assertEqual(
            fake_client.search_recent_tweets.call_count,
            _COMMENTS_MAX_PAGES_X,
            msg="The ceiling is what stops the walk, and X still had more "
            "pages to answer.",
        )
        self.assertTrue(comments["data"])
        for comment in comments["data"]:
            self.assertIsNone(
                comment["reply_count"],
                msg="Counted over an unfinished walk the total would be a "
                "number X never said.",
            )

    def test_get_comments_rate_limited_keeps_the_pages_already_read(self):
        """The quota reached on a later page does not undo the earlier ones.

        Their cost is already paid, and the window of the endpoint is written
        the same, so throwing them away would only leave the user with an
        empty thread.
        """
        fake_client = MagicMock()
        fake_client.search_recent_tweets.side_effect = [
            self._fake_page_x([self._fake_tweet_x("100")], next_token="page_2"),
            self.get_exception_manyrequests(),
        ]
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            comments = self.SocialPostAccountX.get_comments()
        self.assertTrue(comments["success"])
        self.assertEqual(len(comments["data"]), 1)
        self.assertIsNone(comments["data"][0]["reply_count"])
        self.assertEqual(
            self.SocialPostAccountX.account_id.rate_limit_endpoint["get_comments"][
                "x-rate-limit-reset"
            ],
            9999999999,
            msg="The window of the endpoint is written even though the read "
            "answered what it had.",
        )

    @mute_logger(LOGGER_POST_ACCOUNT_X_SYNC)
    def test_create_x_comment_exception(self):
        fake_client = MagicMock()
        fake_client.create_tweet.side_effect = Exception("Error Create Comment")
        # The failure is checked against the post itself, which X answers
        # without errors here: the tweet is still online.
        fake_client.get_tweet.return_value = MagicMock(errors=[])
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            res = self.create_test_comment()
        self.assertFalse(res["success"])
        self.assertFalse(res["post_deleted"])
        self.assertIn("Error Comment Tweet", res["message"])
        self.assertNotEqual(self.SocialPostAccountX.state, "deleted")

    @mute_logger(LOGGER_POST_ACCOUNT_X_SYNC)
    def test_create_x_comment_post_gone(self):
        """X refuses the reply and the post it answers no longer exists."""
        fake_client = MagicMock()
        fake_client.create_tweet.side_effect = Exception("Bad Request")
        fake_client.get_tweet.return_value = MagicMock(
            errors=[{"type": "https://api.twitter.com/2/problems/resource-not-found"}]
        )
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            res = self.create_test_comment()
        self.assertFalse(res["success"])
        self.assertTrue(res["post_deleted"])
        self.assertEqual(res["message"], "The post does not exist or has been deleted.")
        self.assertEqual(self.SocialPostAccountX.state, "deleted")

    def test_create_x_comment_exception_manyrequests(self):
        fake_client = MagicMock()
        fake_client.create_tweet.return_value = False
        fake_client.create_tweet.side_effect = self.get_exception_manyrequests()
        (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests,
        ) = self.get_patch_exceptions_x(fake_client, True)
        with (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests as many_requests,
        ):
            self.create_test_comment()
        many_requests.assert_called_once()

    def test_create_x_comment_rate_limited_is_not_a_published_reply(self):
        """A reply X refused for quota says so instead of answering success.

        The client paints this answer for the user and clears the composer
        with it, so a ``success`` for a tweet X never received loses the text
        and tells the user the reply is out there.
        """
        fake_client = MagicMock()
        fake_client.create_tweet.side_effect = self.get_exception_manyrequests()
        (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests,
        ) = self.get_patch_exceptions_x(fake_client, True)
        with (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests,
        ):
            res = self.create_test_comment()
        self.assertFalse(res["success"])
        self.assertFalse(res["post_deleted"])
        self.assertIn("limit of requests", res["message"])

    def test_create_x_comment_inside_the_quota_window_is_not_a_reply(self):
        """The window of the endpoint still open is not a published reply.

        Nothing is asked to X while the limit lasts, so the answer says the
        reply could not be published instead of saying it was.
        """
        mock_get_client_api = self.get_patch_exceptions_x(
            MagicMock(), valid_time_request=False
        )
        with (
            mock_get_client_api as get_client_api,
            patch.object(
                type(self.SocialPostAccountX.account_id),
                "_valid_time_request",
                autospec=True,
                return_value=False,
            ),
        ):
            res = self.create_test_comment()
        get_client_api.assert_not_called()
        self.assertFalse(res["success"])
        self.assertFalse(res["post_deleted"])
        self.assertIn("limit of requests", res["message"])

    def test_get_assets_save_x(self):
        fake_medias = ["media1"]
        media_map = {"media1": ("media_key1", "www.media_url_1", "media_type1")}
        attachment = self.env["ir.attachment"].create(
            {
                "name": "media_key1",
                "type": "binary",
                "res_model": self.SocialPostAccountX._name,
                "res_id": self.SocialPostAccountX.id,
                "datas": self.image_base64,
            }
        )
        with patch.object(
            type(self.SocialPostAccount),
            "_map_medias_account",
            autospec=True,
            return_value=attachment,
        ) as mock_map_medias:
            attachments, media_refs = self.SocialPostAccountX._get_assets_save_x(
                fake_medias, media_map
            )
            self.assertEqual(attachments, attachment)
            self.assertEqual(attachments.type, "binary")
            self.assertEqual(attachments.res_model, self.SocialPostAccountX._name)
            self.assertEqual(attachments.res_id, self.SocialPostAccountX.id)
            self.assertEqual(
                media_refs,
                {str(attachment.id): "media1"},
                "The media key of the social media is what tells this "
                "attachment apart from one attached in Odoo",
            )
            mock_map_medias.assert_called_once()

    def test_get_assets_save_x_failed(self):
        fake_medias = ["media1"]
        media_map = {"media1": ("media_key1", "www.media_url_1", "media_type1")}
        with patch.object(
            type(self.SocialPostAccount),
            "_get_medias_account",
            autospec=True,
            return_value=["media1"],
        ) as mock_get_medias:
            attachments, media_refs = self.SocialPostAccountX._get_assets_save_x(
                fake_medias, media_map
            )
            self.assertFalse(attachments)
            self.assertEqual(media_refs, {})
            mock_get_medias.assert_called_once()

    def test_get_comments(self):
        now = datetime.now()
        fake_comment = MagicMock()
        fake_comment.id = "comment_id1"
        fake_comment.text = "Comment 1"
        fake_comment.author_id = "author_1"
        fake_comment.created_at = now
        fake_user = MagicMock()
        fake_user.id = "author_1"
        fake_user.created_at = now
        fake_user.profile_image_url = "https://www.fake.media/url_image"
        fake_comment.attachments = {"media_keys": ["media_key_1"]}
        fake_media = MagicMock()
        fake_media.media_key = "media_key_1"
        fake_media.url = "https://www.fake.media/comment_image.jpg"
        fake_response = MagicMock()
        fake_response.data = [fake_comment]
        fake_response.includes = {"users": [fake_user], "media": [fake_media]}
        fake_response.errors = self.test_response_errors
        fake_response.meta = {}
        fake_client = MagicMock()
        fake_client.search_recent_tweets.return_value = fake_response
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            comments = self.SocialPostAccountX.get_comments()
            self.assertEqual(len(comments["data"]), 1)
            self.assertEqual(comments["data"][0]["id"], "comment_id1")
            self.assertEqual(comments["data"][0]["text"], "Comment 1")
            self.assertEqual(
                comments["data"][0]["images_url"],
                ["https://www.fake.media/comment_image.jpg"],
                msg="The media of a comment comes from response.includes, "
                "not from the comment itself.",
            )

    def test_get_comments_without_media(self):
        fake_comment = MagicMock()
        fake_comment.id = "comment_id1"
        fake_comment.text = "Comment 1"
        fake_comment.author_id = "author_1"
        fake_comment.created_at = datetime.now()
        fake_comment.attachments = None
        fake_user = MagicMock()
        fake_user.id = "author_1"
        fake_user.profile_image_url = "https://www.fake.media/url_image"
        fake_response = MagicMock()
        fake_response.data = [fake_comment]
        fake_response.includes = {"users": [fake_user]}
        fake_response.errors = self.test_response_errors
        fake_response.meta = {}
        fake_client = MagicMock()
        fake_client.search_recent_tweets.return_value = fake_response
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            comments = self.SocialPostAccountX.get_comments()
        self.assertEqual(comments["data"][0]["images_url"], [])

    @mute_logger(LOGGER_POST_ACCOUNT_X_SYNC)
    def test_get_comments_exception(self):
        fake_client = MagicMock()
        fake_client.search_recent_tweets.side_effect = Exception("Error Comments")
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            res = self.SocialPostAccountX.get_comments()
        self.assertFalse(res["success"])
        self.assertIn("Error Get Comments for Tweet", res["message"])

    def test_get_comments_exception_manyrequests(self):
        fake_client = MagicMock()
        fake_client.search_recent_tweets.side_effect = self.get_exception_manyrequests()
        (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests,
        ) = self.get_patch_exceptions_x(fake_client, True)
        with (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests as many_requests,
        ):
            self.SocialPostAccountX.get_comments()
        many_requests.assert_called_once()

    def test_get_comments_rate_limited_is_not_an_empty_thread(self):
        """A read X refused for quota says so instead of answering nothing.

        The client replaces the comments on screen with what this answers, so
        a ``success`` carrying an empty list is indistinguishable from a
        publication with no comments and takes the visible thread with it.
        """
        fake_client = MagicMock()
        fake_client.search_recent_tweets.side_effect = self.get_exception_manyrequests()
        (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests,
        ) = self.get_patch_exceptions_x(fake_client, True)
        with (
            mock_get_client_api,
            mock_valid_time_request,
            mock_many_requests,
        ):
            res = self.SocialPostAccountX.get_comments()
        self.assertFalse(res["success"])
        self.assertIn("limit of requests", res["message"])

    def test_get_comments_inside_the_quota_window_is_not_an_empty_thread(self):
        """The window of the endpoint still open is not an empty thread.

        Nothing is asked to X while the limit lasts, so the answer says the
        comments could not be read instead of saying there are none.
        """
        mock_get_client_api = self.get_patch_exceptions_x(
            MagicMock(), valid_time_request=False
        )
        with (
            mock_get_client_api as get_client_api,
            patch.object(
                type(self.SocialPostAccountX.account_id),
                "_valid_time_request",
                autospec=True,
                return_value=False,
            ),
        ):
            res = self.SocialPostAccountX.get_comments()
        get_client_api.assert_not_called()
        self.assertFalse(res["success"])
        self.assertIn("limit of requests", res["message"])

    def test_get_comments_answers_another_media_verbatim(self):
        """The comments of another social media come back untouched.

        This connector is the outermost of the chain, so it is the last one
        able to rewrite an answer that is not its own: ``success`` and the
        message explaining a failure of another network travel back whole, not
        only the comments in ``data``.
        """
        answer = {
            "success": False,
            "message": "Only the media of the publication answers.",
            "data": [{"id": "foreign"}],
        }
        with patch(PATCH_SYNC_POST_ACCOUNT.format("get_comments"), return_value=answer):
            self.assertEqual(self.SocialPostAccount.get_comments(), answer)

    def test_x_comment_parent_ref_reads_past_a_quote(self):
        """A tweet quoting another one still hangs from what it answers.

        ``referenced_tweets`` holds every tweet the reply points at, and only
        the one it replied to says where the comment belongs.
        """
        tweet = MagicMock()
        tweet.referenced_tweets = [
            MagicMock(type="quoted", id="quoted_1"),
            MagicMock(type="replied_to", id="comment_1"),
        ]
        self.assertEqual(
            self.SocialPostAccountX._x_comment_parent_ref(tweet, {"comment_1"}),
            "comment_1",
        )
        self.assertFalse(
            self.SocialPostAccountX._x_comment_parent_ref(tweet, set()),
            msg="A comment answering what no page brought hangs from the post.",
        )

    def test_x_comment_parent_ref_of_a_quote_alone(self):
        """A tweet that only quotes answers nothing of the thread."""
        tweet = MagicMock()
        tweet.referenced_tweets = [MagicMock(type="quoted", id="quoted_1")]
        self.assertFalse(
            self.SocialPostAccountX._x_comment_parent_ref(tweet, {"quoted_1"})
        )

    def test_get_comments_skips_a_media_without_address(self):
        """A media X names but does not address cannot be drawn.

        What travels to the client is the address of the image, so a media
        without one is left out instead of reaching it as an empty source.
        """
        fake_comment = MagicMock()
        fake_comment.id = "comment_id1"
        fake_comment.text = "Comment 1"
        fake_comment.author_id = "author_1"
        fake_comment.created_at = datetime.now()
        fake_comment.attachments = {"media_keys": ["media_key_1"]}
        fake_comment.referenced_tweets = None
        fake_user = MagicMock()
        fake_user.id = "author_1"
        fake_user.profile_image_url = None
        fake_media = MagicMock()
        fake_media.media_key = "media_key_1"
        fake_media.url = None
        fake_response = MagicMock()
        fake_response.data = [fake_comment]
        fake_response.includes = {"users": [fake_user], "media": [fake_media]}
        fake_response.meta = {}
        fake_client = MagicMock()
        fake_client.search_recent_tweets.return_value = fake_response
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            comments = self.SocialPostAccountX.get_comments()
        self.assertEqual(comments["data"][0]["images_url"], [])

    def test_create_x_comment_of_another_media_writes_no_tweet(self):
        """The publication of another social media is not X's to reply to.

        The method runs on the whole chain, so what answers for a publication
        that is not X's is the shape of a reply nobody had to write here.
        """
        with patch.object(
            type(self.SocialAccount), "get_client_api", autospec=True
        ) as mock_get_client_api:
            self.assertEqual(
                self.social_post_account_id.create_x_comment(self.post_data),
                {"success": True, "post_deleted": False},
            )
        mock_get_client_api.assert_not_called()

    def test_the_search_panel_filters_the_figures_of_x(self):
        """Reposts and quotes are searched where they are imported.

        The two filters arrive with this bridge, applied over the search view
        of the base module, and each one answers the publications whose
        figure this module writes.
        """
        view = self.env.ref(
            "social_media_x_sync.social_post_account_view_search_inherit"
        )
        self.assertEqual(
            view.inherit_id,
            self.env.ref("social_media_base.social_post_account_view_search"),
        )
        arch = etree.fromstring(
            self.SocialPostAccount.get_view(
                self.env.ref("social_media_base.social_post_account_view_search").id,
                "search",
            )["arch"]
        )
        reposted = self.SocialPostAccountX
        reposted.write({"retweet_count": 3, "quote_count": 0})
        quoted = self.SocialPostAccount.create(
            {
                "message": "Quoted publication",
                "account_id": self.SocialAccountX.id,
                "media_id": self.media_x_id.id,
                "post_id": self.SocialPostX.id,
                "state": "posted",
                "remote_ref": "159753457",
                "retweet_count": 0,
                "quote_count": 5,
            }
        )
        for filter_name, expected in (
            ("with_reposts", reposted),
            ("with_quotes", quoted),
        ):
            nodes = arch.xpath(f"//filter[@name='{filter_name}']")
            self.assertTrue(
                nodes, msg=f"{filter_name} has to be offered by this module."
            )
            domain = literal_eval(nodes[0].get("domain"))
            found = self.SocialPostAccount.search(
                domain + [("id", "in", (reposted + quoted).ids)]
            )
            self.assertEqual(
                found,
                expected,
                msg=f"{filter_name} has to answer only what carries that figure.",
            )
