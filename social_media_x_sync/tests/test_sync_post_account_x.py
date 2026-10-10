# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from ast import literal_eval
from datetime import datetime
from unittest.mock import MagicMock, patch

from lxml import etree
from tweepy.errors import Forbidden, NotFound, Unauthorized

from odoo import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.social_media_sync.tests.test_social_sync_common import (
    PATCH_SYNC_POST_ACCOUNT,
    media_download_response,
)
from odoo.addons.social_media_x.social_x_utils import _URL_PRICING_X

from ..models.social_post_account import SocialPostAccount as XSyncSocialPostAccount
from ..social_x_sync_utils import (
    _COMMENTS_MAX_PAGES_X,
    _LIKED_TWEETS_MAX_RESULTS_X,
    _SEARCH_MAX_RESULTS_X,
    _SKIP_LIKES_CONTEXT_X,
)
from .test_sync_x_common import (
    LOGGER_ACCOUNT_X_SYNC,
    LOGGER_POST_ACCOUNT_X_SYNC,
    VIDEO_BEST_URL_X,
    VIDEO_VARIANTS_X,
    TestSocialSyncCommonX,
)


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

    def test_x_media_download_url_of_a_video_is_its_best_mp4(self):
        self.assertEqual(
            self.SocialPostAccount._x_media_download_url(
                "video", None, VIDEO_VARIANTS_X
            ),
            VIDEO_BEST_URL_X,
            "The mp4 with the highest bit rate is the one downloaded, and "
            "the HLS playlist is never chosen",
        )

    def test_x_media_download_url_of_an_animated_gif_is_its_mp4(self):
        gif_url = "https://video.twimg.com/tweet_video/gif.mp4"
        self.assertEqual(
            self.SocialPostAccount._x_media_download_url(
                "animated_gif",
                None,
                [{"bit_rate": 0, "content_type": "video/mp4", "url": gif_url}],
            ),
            gif_url,
        )

    def test_x_media_download_url_of_a_video_without_mp4_is_nothing(self):
        self.assertFalse(
            self.SocialPostAccount._x_media_download_url(
                "video",
                None,
                [
                    variant
                    for variant in VIDEO_VARIANTS_X
                    if variant["content_type"] != "video/mp4"
                ],
            )
        )

    def test_x_media_download_url_of_a_photo_is_its_url(self):
        self.assertEqual(
            self.SocialPostAccount._x_media_download_url(
                "photo", "https://pbs.twimg.com/media/photo.jpg", None
            ),
            "https://pbs.twimg.com/media/photo.jpg",
        )

    def test_get_assets_save_x(self):
        fake_medias = ["media1"]
        media_map = {"media1": ("media1", "www.media_url_1", "photo", None)}
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
            images, videos, media_refs = self.SocialPostAccountX._get_assets_save_x(
                fake_medias, media_map
            )
            self.assertEqual(images, attachment)
            self.assertFalse(videos)
            self.assertEqual(images.type, "binary")
            self.assertEqual(images.res_model, self.SocialPostAccountX._name)
            self.assertEqual(images.res_id, self.SocialPostAccountX.id)
            self.assertEqual(
                media_refs,
                {str(attachment.id): "media1"},
                "The media key of the social media is what tells this "
                "attachment apart from one attached in Odoo",
            )
            mock_map_medias.assert_called_once()

    def test_get_assets_save_x_failed(self):
        fake_medias = ["media1"]
        media_map = {"media1": ("media1", "www.media_url_1", "photo", None)}
        with patch.object(
            type(self.SocialPostAccount),
            "_get_medias_account",
            autospec=True,
            return_value=["media1"],
        ) as mock_get_medias:
            images, videos, media_refs = self.SocialPostAccountX._get_assets_save_x(
                fake_medias, media_map
            )
            self.assertFalse(images)
            self.assertFalse(videos)
            self.assertEqual(media_refs, {})
            mock_get_medias.assert_called_once()

    def test_get_assets_save_x_splits_the_photos_from_the_videos(self):
        photo_url = "https://pbs.twimg.com/media/photo.jpg"
        media_map = {
            "photo1": ("photo1", photo_url, "photo", None),
            "video1": ("video1", None, "video", VIDEO_VARIANTS_X),
        }
        downloads = {
            photo_url: media_download_response([b"photo"]),
            VIDEO_BEST_URL_X: media_download_response([b"video"]),
        }
        with patch(
            "requests.get", side_effect=lambda url, **kwargs: downloads[url]
        ) as mock_get:
            images, videos, media_refs = self.SocialPostAccountX._get_assets_save_x(
                ["photo1", "video1"], media_map
            )
        self.assertEqual(images.mapped("name"), ["photo1"])
        self.assertEqual(videos.mapped("name"), ["video1"])
        self.assertEqual(
            videos.mimetype,
            "video/mp4",
            "The name of the attachment is the media key, with no extension "
            "to tell an mp4 by, so its type is given explicitly",
        )
        self.assertEqual(
            media_refs,
            {str(images.id): "photo1", str(videos.id): "video1"},
        )
        self.assertEqual(
            {call.args[0] for call in mock_get.call_args_list},
            {photo_url, VIDEO_BEST_URL_X},
        )

    def test_get_assets_save_x_stores_the_videos_through_social_media_sync(self):
        """The videos of X are downloaded by the hook every bridge shares."""
        media_map = {"video1": ("video1", None, "video", VIDEO_VARIANTS_X)}
        with patch.object(
            type(self.SocialPostAccount),
            "_store_remote_videos",
            autospec=True,
            return_value=(self.env["ir.attachment"], {}),
        ) as mock_store_videos:
            self.SocialPostAccountX._get_assets_save_x(["video1"], media_map)
        mock_store_videos.assert_called_once_with(
            self.SocialPostAccountX,
            {"video1": VIDEO_BEST_URL_X},
            mimetype="video/mp4",
        )

    def test_get_assets_save_x_skips_a_video_already_stored(self):
        video = self.env["ir.attachment"].create(
            {"name": "video1", "mimetype": "video/mp4", "raw": b"video"}
        )
        self.SocialPostAccountX.write(
            {
                "video_ids": [Command.link(video.id)],
                "media_refs": {str(video.id): "video1"},
            }
        )
        media_map = {"video1": ("video1", None, "video", VIDEO_VARIANTS_X)}
        with patch.object(
            type(self.SocialPostAccount), "_map_medias_account", autospec=True
        ) as mock_map_medias:
            images, videos, media_refs = self.SocialPostAccountX._get_assets_save_x(
                ["video1"], media_map
            )
        mock_map_medias.assert_not_called()
        self.assertFalse(images)
        self.assertFalse(videos)
        self.assertEqual(media_refs, {})

    @mute_logger("odoo.addons.social_media_sync.models.social_post_account")
    def test_get_assets_save_x_a_failed_video_download_stores_nothing(self):
        media_map = {"video1": ("video1", None, "video", VIDEO_VARIANTS_X)}
        attachments_before = self.env["ir.attachment"].search_count([])
        with patch(
            "requests.get", return_value=media_download_response(status_code=500)
        ):
            images, videos, media_refs = self.SocialPostAccountX._get_assets_save_x(
                ["video1"], media_map
            )
        self.assertFalse(images)
        self.assertFalse(videos)
        self.assertEqual(media_refs, {})
        self.assertEqual(self.env["ir.attachment"].search_count([]), attachments_before)

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
        with neither ``url`` nor ``preview_image_url`` is left out instead of
        reaching it as an empty source.
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
        fake_media.type = "video"
        fake_media.url = None
        fake_media.preview_image_url = None
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

    def _get_comments_with_medias(self, medias, text="Comment 1", entities=None):
        """Read a thread of one comment carrying ``medias``.

        :param medias: the media X reports for the comment, in its order.
        :param text: the text of the comment, as X answers it.
        :param entities: the ``entities`` X answers for the comment.
        :return: what ``get_comments`` answered and the mock of the client.
        :rtype: tuple
        """
        fake_comment = MagicMock()
        fake_comment.id = "comment_id1"
        fake_comment.text = text
        fake_comment.author_id = "author_1"
        fake_comment.created_at = datetime.now()
        fake_comment.attachments = {"media_keys": [media.media_key for media in medias]}
        fake_comment.entities = entities
        fake_comment.referenced_tweets = None
        fake_user = MagicMock()
        fake_user.id = "author_1"
        fake_user.profile_image_url = None
        fake_response = MagicMock()
        fake_response.data = [fake_comment]
        fake_response.includes = {"users": [fake_user], "media": medias}
        fake_response.meta = {}
        fake_client = MagicMock()
        fake_client.search_recent_tweets.return_value = fake_response
        (
            mock_get_client_api,
            mock_valid_time_request,
        ) = self.get_patch_exceptions_x(fake_client)
        with mock_get_client_api, mock_valid_time_request:
            comments = self.SocialPostAccountX.get_comments()
        return comments, fake_client

    def test_get_comments_asks_for_the_cover_of_the_videos(self):
        _comments, fake_client = self._get_comments_with_medias([])
        self.assertIn(
            "preview_image_url",
            fake_client.search_recent_tweets.call_args.kwargs["media_fields"],
        )

    def test_get_comments_draws_the_cover_of_a_video(self):
        comments, _fake_client = self._get_comments_with_medias(
            [
                MagicMock(
                    media_key="video1",
                    type="video",
                    url=None,
                    preview_image_url="https://pbs.twimg.com/video_cover.jpg",
                ),
                MagicMock(
                    media_key="photo1",
                    type="photo",
                    url="https://pbs.twimg.com/media/photo.jpg",
                    preview_image_url=None,
                ),
            ]
        )
        self.assertEqual(
            comments["data"][0]["images_url"],
            [
                "https://pbs.twimg.com/video_cover.jpg",
                "https://pbs.twimg.com/media/photo.jpg",
            ],
        )

    def test_get_comments_draws_the_cover_of_an_animated_gif(self):
        comments, _fake_client = self._get_comments_with_medias(
            [
                MagicMock(
                    media_key="gif1",
                    type="animated_gif",
                    url=None,
                    preview_image_url="https://pbs.twimg.com/gif_cover.jpg",
                )
            ]
        )
        self.assertEqual(
            comments["data"][0]["images_url"],
            ["https://pbs.twimg.com/gif_cover.jpg"],
        )

    def test_get_comments_asks_for_the_entities(self):
        """The links of the media are told apart in the same call."""
        _comments, fake_client = self._get_comments_with_medias([])
        self.assertIn(
            "entities",
            fake_client.search_recent_tweets.call_args.kwargs["tweet_fields"],
        )

    def test_get_comments_strips_the_link_of_an_animated_gif(self):
        """A reply with a GIF draws its cover and keeps the links its author wrote."""
        comments, _fake_client = self._get_comments_with_medias(
            [
                MagicMock(
                    media_key="gif1",
                    type="animated_gif",
                    url=None,
                    preview_image_url="https://pbs.twimg.com/gif_cover.jpg",
                )
            ],
            text="Look https://t.co/author https://t.co/gif",
            entities={
                "urls": [
                    {"url": "https://t.co/author"},
                    {"url": "https://t.co/gif", "media_key": "gif1"},
                ]
            },
        )
        self.assertEqual(comments["data"][0]["text"], "Look https://t.co/author ")
        self.assertEqual(
            comments["data"][0]["images_url"],
            ["https://pbs.twimg.com/gif_cover.jpg"],
        )

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

    def test_the_list_offers_the_reposts_and_the_quotes(self):
        """Both figures are optional columns, hidden, right after the shares."""
        arch = etree.fromstring(
            self.SocialPostAccount.get_view(
                self.env.ref("social_media_base.social_post_account_view_tree").id,
                "tree",
            )["arch"]
        )
        names = [field.get("name") for field in arch.xpath("/tree/field")]
        share_index = names.index("share_count")
        self.assertEqual(
            names[share_index + 1 : share_index + 3],
            ["retweet_count", "quote_count"],
        )
        for name in ("retweet_count", "quote_count"):
            self.assertEqual(
                arch.xpath(f"/tree/field[@name='{name}']")[0].get("optional"),
                "hide",
            )


@tagged("post_install", "-at_install")
class TestSocialSyncReactionX(TestSocialSyncCommonX):
    """The like of the account on a publication and on a comment of X."""

    NOT_FOUND_ERRORS_X = [
        {"type": "https://api.twitter.com/2/problems/resource-not-found"}
    ]

    def _client_liking(self, liked):
        """Return a client of X that answers the like with ``liked``."""
        fake_client = MagicMock()
        fake_client.like.return_value = MagicMock(data={"liked": liked}, errors=[])
        fake_client.unlike.return_value = MagicMock(data={"liked": liked}, errors=[])
        return fake_client

    def _patch_super(self, method, answer):
        """Patch what the chain answers below this bridge for ``method``."""
        return self.get_patch_super_x(
            self.SocialPostAccountX,
            XSyncSocialPostAccount,
            method,
            return_value=answer,
        )

    def test_like_post_writes_what_x_answers(self):
        fake_client = self._client_liking(True)
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request as valid_time_request:
            res = self.SocialPostAccountX.action_like_post()
        self.assertEqual(
            res,
            {"success": True, "message": "", "post_deleted": False, "liked": True},
        )
        self.assertTrue(self.SocialPostAccountX.liked_by_account)
        fake_client.like.assert_called_once_with("159753456")
        valid_time_request.assert_called_once_with(self.SocialAccountX, endpoint="like")

    def test_unlike_post_writes_what_x_answers(self):
        self.SocialPostAccountX.liked_by_account = True
        fake_client = self._client_liking(False)
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            res = self.SocialPostAccountX.action_unlike_post()
        self.assertTrue(res["success"])
        self.assertFalse(res["liked"])
        self.assertFalse(self.SocialPostAccountX.liked_by_account)
        fake_client.unlike.assert_called_once_with("159753456")
        fake_client.like.assert_not_called()

    def test_like_post_keeps_what_x_holds_over_what_was_asked(self):
        """Withdrawing a like X still reports is answered as still given."""
        self.SocialPostAccountX.liked_by_account = True
        fake_client = self._client_liking(True)
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            res = self.SocialPostAccountX.action_unlike_post()
        self.assertTrue(res["liked"])
        self.assertTrue(self.SocialPostAccountX.liked_by_account)

    def test_like_post_ignores_the_actor_of_the_call(self):
        """The like is given as the account, whatever the client names."""
        fake_client = self._client_liking(True)
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api as get_client_api, mock_valid_time_request:
            self.SocialPostAccountX.action_like_post(author_urn="SOMEBODY_ELSE")
        # The user context of the account, with its own tokens and nothing
        # passed in from the call.
        get_client_api.assert_called_once_with(self.SocialAccountX)
        fake_client.like.assert_called_once_with("159753456")

    def test_like_post_rate_limited_keeps_the_recommendation(self):
        fake_client = MagicMock()
        fake_client.like.side_effect = self.get_exception_manyrequests()
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
            res = self.SocialPostAccountX.action_like_post()
        self.assertFalse(res["success"])
        self.assertFalse(res["liked"])
        self.assertFalse(res["post_deleted"])
        self.assertIn("limit of requests", res["message"])
        self.assertFalse(self.SocialPostAccountX.liked_by_account)
        self.assertEqual(many_requests.call_args.kwargs, {"endpoint": "like"})

    def test_like_post_inside_the_quota_window_asks_nothing(self):
        mock_get_client_api = self.get_patch_exceptions_x(
            MagicMock(), valid_time_request=False
        )
        with (
            mock_get_client_api as get_client_api,
            patch.object(
                type(self.SocialAccountX),
                "_valid_time_request",
                autospec=True,
                return_value=False,
            ),
        ):
            res = self.SocialPostAccountX.action_like_post()
        get_client_api.assert_not_called()
        self.assertFalse(res["success"])
        self.assertIn("limit of requests", res["message"])
        self.assertFalse(self.SocialPostAccountX.liked_by_account)

    def test_like_post_refused_credentials_flag_the_account(self):
        fake_client = MagicMock()
        fake_client.like.side_effect = self.get_x_refusal(
            Unauthorized, 401, "Unauthorized"
        )
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with (
            mock_get_client_api,
            mock_valid_time_request,
            patch.object(
                type(self.SocialAccountX), "_flag_credentials_expired", autospec=True
            ) as flag_credentials_expired,
        ):
            res = self.SocialPostAccountX.action_like_post()
        flag_credentials_expired.assert_called_once()
        self.assertFalse(res["success"])
        self.assertFalse(res["post_deleted"])
        self.assertIn("credentials", res["message"])
        self.assertFalse(self.SocialPostAccountX.liked_by_account)

    def test_like_post_forbidden_explains_the_plan(self):
        """A ``403`` of an App without a paid plan says what to do about it."""
        fake_client = MagicMock()
        fake_client.like.side_effect = self.get_x_refusal(
            Forbidden, 403, "client-not-enrolled"
        )
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with (
            mock_get_client_api,
            mock_valid_time_request,
            patch.object(
                type(self.SocialAccountX), "_flag_credentials_expired", autospec=True
            ) as flag_credentials_expired,
        ):
            res = self.SocialPostAccountX.action_like_post()
        flag_credentials_expired.assert_not_called()
        self.assertFalse(res["success"])
        self.assertIn("Pay Per Use", res["message"])
        # Drawn as plain text, so the link travels as its address.
        self.assertIn(_URL_PRICING_X, res["message"])
        self.assertNotIn("<a ", res["message"])

    @mute_logger(LOGGER_POST_ACCOUNT_X_SYNC)
    def test_like_post_gone_answers_post_deleted(self):
        fake_client = MagicMock()
        fake_client.like.return_value = MagicMock(
            data=None, errors=self.NOT_FOUND_ERRORS_X
        )
        fake_client.get_tweet.return_value = MagicMock(errors=self.NOT_FOUND_ERRORS_X)
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            res = self.SocialPostAccountX.action_like_post()
        self.assertFalse(res["success"])
        self.assertTrue(res["post_deleted"])
        self.assertEqual(res["message"], "The post does not exist or has been deleted.")
        self.assertEqual(self.SocialPostAccountX.state, "deleted")
        self.assertFalse(self.SocialPostAccountX.liked_by_account)

    @mute_logger(LOGGER_POST_ACCOUNT_X_SYNC)
    def test_like_post_unknown_error_leaves_the_post_alone(self):
        fake_client = MagicMock()
        fake_client.like.side_effect = Exception("Something broke")
        fake_client.get_tweet.return_value = MagicMock(errors=[])
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            res = self.SocialPostAccountX.action_like_post()
        self.assertFalse(res["success"])
        self.assertFalse(res["post_deleted"])
        self.assertIn("Error Recommend Tweet", res["message"])
        self.assertNotEqual(self.SocialPostAccountX.state, "deleted")

    def test_like_comment_without_reference_asks_nothing(self):
        mock_get_client_api = self.get_patch_exceptions_x(
            MagicMock(), valid_time_request=False
        )
        with mock_get_client_api as get_client_api:
            res = self.SocialPostAccountX.action_like_comment()
        get_client_api.assert_not_called()
        self.assertFalse(res["success"])
        self.assertIsNone(res["liked"])

    def test_like_comment_answers_what_x_holds_and_stores_nothing(self):
        fake_client = self._client_liking(True)
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            res = self.SocialPostAccountX.action_like_comment(
                comment_ref="777", author_urn="SOMEBODY_ELSE"
            )
        self.assertTrue(res["success"])
        self.assertTrue(res["liked"])
        fake_client.like.assert_called_once_with("777")
        # The like of a comment is read again when the dialog opens, never
        # kept on the publication.
        self.assertFalse(self.SocialPostAccountX.liked_by_account)

    def test_unlike_comment_answers_what_x_holds(self):
        fake_client = self._client_liking(False)
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            res = self.SocialPostAccountX.action_unlike_comment(comment_ref="777")
        self.assertTrue(res["success"])
        self.assertFalse(res["liked"])
        fake_client.unlike.assert_called_once_with("777")

    @mute_logger(LOGGER_POST_ACCOUNT_X_SYNC)
    def test_like_comment_unknown_error_says_nothing_of_the_like(self):
        """An error that names nothing does not redraw the entry."""
        fake_client = MagicMock()
        fake_client.like.side_effect = Exception("Something broke")
        fake_client.get_tweet.return_value = MagicMock(errors=[])
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            res = self.SocialPostAccountX.action_like_comment(comment_ref="777")
        self.assertFalse(res["success"])
        self.assertIsNone(res["liked"])
        self.assertFalse(res["post_deleted"])

    def test_reactions_of_another_media_answer_the_chain(self):
        """What the chain answers for another social media comes back whole."""
        answer = {
            "success": False,
            "message": "Only the media of the publication answers.",
            "post_deleted": False,
            "liked": None,
        }
        calls = {
            "action_like_post": {},
            "action_unlike_post": {},
            "action_like_comment": {"comment_ref": "777"},
            "action_unlike_comment": {"comment_ref": "777"},
        }
        for method, kwargs in calls.items():
            with (
                self.subTest(method=method),
                self._patch_super(method, answer),
                patch.object(
                    type(self.SocialPostAccountX), "_x_react", autospec=True
                ) as x_react,
            ):
                res = getattr(self.social_post_account_id, method)(**kwargs)
                self.assertEqual(res, answer)
                x_react.assert_not_called()


@tagged("post_install", "-at_install")
class TestSocialSyncCommentLikesX(TestSocialSyncCommonX):
    """What the comments of X say about the account: its likes and its own."""

    def _client_with_thread(self):
        """Return a client of X answering a thread of two comments.

        One of them is written by the account and the other one by somebody
        else; the page of likes holds the second one only.
        """
        comments = []
        for ref, author_ref in (
            ("own_comment", self.SocialAccountX.remote_ref),
            ("liked_comment", "somebody_else"),
        ):
            comment = MagicMock(
                id=ref,
                text=f"Comment {ref}",
                author_id=author_ref,
                created_at=datetime(2026, 3, 1, 8, 0),
                attachments=None,
                entities=None,
                referenced_tweets=None,
            )
            comments.append(comment)
        users = [
            MagicMock(id=self.SocialAccountX.remote_ref, profile_image_url=None),
            MagicMock(id="somebody_else", profile_image_url=None),
        ]
        fake_client = MagicMock()
        fake_client.search_recent_tweets.return_value = MagicMock(
            data=comments, includes={"users": users}, errors=[], meta={}
        )
        fake_client.get_liked_tweets.return_value = MagicMock(
            data=[MagicMock(id="liked_comment"), MagicMock(id="a_publication")],
            errors=[],
        )
        return fake_client

    def _get_comments(self, fake_client, context=None):
        """Read the comments of the publication through ``fake_client``."""
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            res = self.SocialPostAccountX.with_context(**(context or {})).get_comments()
        self.assertTrue(res["success"])
        return {comment["remote_ref"]: comment for comment in res["data"]}

    def test_get_comments_says_which_ones_the_account_liked(self):
        fake_client = self._client_with_thread()
        comments = self._get_comments(fake_client)
        self.assertTrue(comments["liked_comment"]["liked"])
        self.assertFalse(comments["own_comment"]["liked"])
        fake_client.get_liked_tweets.assert_called_once_with(
            self.SocialAccountX.remote_ref,
            max_results=_LIKED_TWEETS_MAX_RESULTS_X,
            tweet_fields=["id"],
            user_auth=True,
        )

    def test_get_comments_says_who_wrote_each_one(self):
        comments = self._get_comments(self._client_with_thread())
        self.assertEqual(
            comments["own_comment"]["author_ref"], self.SocialAccountX.remote_ref
        )
        self.assertEqual(comments["liked_comment"]["author_ref"], "somebody_else")

    def test_get_comments_of_a_refresh_reads_no_likes(self):
        """The dialog already holds the likes of what it draws."""
        fake_client = self._client_with_thread()
        comments = self._get_comments(
            fake_client, context={_SKIP_LIKES_CONTEXT_X: True}
        )
        fake_client.get_liked_tweets.assert_not_called()
        self.assertFalse(comments["liked_comment"]["liked"])
        self.assertEqual(comments["liked_comment"]["author_ref"], "somebody_else")

    @mute_logger(LOGGER_ACCOUNT_X_SYNC)
    def test_get_comments_without_the_likes_still_answers_the_thread(self):
        fake_client = self._client_with_thread()
        fake_client.get_liked_tweets.side_effect = Exception("Something broke")
        comments = self._get_comments(fake_client)
        self.assertEqual(set(comments), {"own_comment", "liked_comment"})
        self.assertFalse(comments["liked_comment"]["liked"])

    def test_get_comments_of_an_empty_thread_reads_no_likes(self):
        fake_client = MagicMock()
        fake_client.search_recent_tweets.return_value = MagicMock(
            data=None, includes={}, errors=[], meta={}
        )
        self._get_comments(fake_client)
        fake_client.get_liked_tweets.assert_not_called()

    def test_created_comment_is_written_by_the_account(self):
        fake_client = MagicMock()
        fake_client.create_tweet.return_value = MagicMock(
            data={"id": 9876543210, "text": "A reply"}
        )
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            result = self.SocialPostAccountX.create_x_comment({"body": "A reply"})
        self.assertEqual(
            result["comment"]["author_ref"], self.SocialAccountX.remote_ref
        )
        self.assertFalse(result["comment"]["liked"])


@tagged("post_install", "-at_install")
class TestSocialSyncDeleteCommentX(TestSocialSyncCommonX):
    """The deletion of a comment the account wrote on X."""

    def _delete(self, fake_client):
        """Delete the comment ``777`` through ``fake_client``."""
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with mock_get_client_api, mock_valid_time_request:
            return self.SocialPostAccountX.delete_comment("777")

    def test_delete_comment_deletes_the_tweet_as_the_account(self):
        fake_client = MagicMock()
        fake_client.delete_tweet.return_value = MagicMock(
            data={"deleted": True}, errors=[]
        )
        mock_get_client_api, mock_valid_time_request = self.get_patch_exceptions_x(
            fake_client
        )
        with (
            mock_get_client_api as get_client_api,
            mock_valid_time_request as valid_time_request,
        ):
            res = self.SocialPostAccountX.delete_comment("777")
        self.assertEqual(res, {"success": True})
        fake_client.delete_tweet.assert_called_once_with("777")
        get_client_api.assert_called_once_with(self.SocialAccountX)
        valid_time_request.assert_called_once_with(
            self.SocialAccountX, endpoint="delete_comment"
        )

    def test_delete_comment_already_gone_is_deleted(self):
        """What was asked for is done, whichever way X says it."""
        answered = MagicMock()
        answered.delete_tweet.return_value = MagicMock(
            data=None,
            errors=[{"type": "https://api.twitter.com/2/problems/resource-not-found"}],
        )
        raised = MagicMock()
        raised.delete_tweet.side_effect = self.get_x_refusal(NotFound, 404, "Not Found")
        for fake_client in (answered, raised):
            self.assertEqual(self._delete(fake_client), {"success": True})

    def test_delete_comment_of_another_author_is_refused(self):
        fake_client = MagicMock()
        fake_client.delete_tweet.side_effect = self.get_x_refusal(
            Forbidden, 403, "You are not allowed to delete this Tweet."
        )
        with patch.object(
            type(self.SocialAccountX), "_flag_credentials_expired", autospec=True
        ) as flag_credentials_expired:
            res = self._delete(fake_client)
        flag_credentials_expired.assert_not_called()
        self.assertFalse(res["success"])
        self.assertIn("You are not allowed to delete this Tweet", res["message"])

    def test_delete_comment_rate_limited(self):
        fake_client = MagicMock()
        fake_client.delete_tweet.side_effect = self.get_exception_manyrequests()
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
            res = self.SocialPostAccountX.delete_comment("777")
        self.assertFalse(res["success"])
        self.assertIn("limit of requests", res["message"])
        self.assertEqual(many_requests.call_args.kwargs, {"endpoint": "delete_comment"})

    def test_delete_comment_inside_the_quota_window_asks_nothing(self):
        mock_get_client_api = self.get_patch_exceptions_x(
            MagicMock(), valid_time_request=False
        )
        with (
            mock_get_client_api as get_client_api,
            patch.object(
                type(self.SocialAccountX),
                "_valid_time_request",
                autospec=True,
                return_value=False,
            ),
        ):
            res = self.SocialPostAccountX.delete_comment("777")
        get_client_api.assert_not_called()
        self.assertFalse(res["success"])
        self.assertIn("limit of requests", res["message"])

    def test_delete_comment_refused_credentials_flag_the_account(self):
        fake_client = MagicMock()
        fake_client.delete_tweet.side_effect = self.get_x_refusal(
            Unauthorized, 401, "Unauthorized"
        )
        with patch.object(
            type(self.SocialAccountX), "_flag_credentials_expired", autospec=True
        ) as flag_credentials_expired:
            res = self._delete(fake_client)
        flag_credentials_expired.assert_called_once()
        self.assertFalse(res["success"])
        self.assertIn("credentials", res["message"])

    @mute_logger(LOGGER_POST_ACCOUNT_X_SYNC)
    def test_delete_comment_unknown_error(self):
        fake_client = MagicMock()
        fake_client.delete_tweet.side_effect = Exception("Something broke")
        res = self._delete(fake_client)
        self.assertFalse(res["success"])
        self.assertIn("Error Delete Comment", res["message"])

    @mute_logger(LOGGER_POST_ACCOUNT_X_SYNC)
    def test_delete_comment_not_deleted_by_x(self):
        fake_client = MagicMock()
        fake_client.delete_tweet.return_value = MagicMock(
            data={"deleted": False}, errors=["Refused"]
        )
        res = self._delete(fake_client)
        self.assertFalse(res["success"])
        self.assertIn("Refused", res["message"])

    def test_delete_comment_of_another_media_answers_the_chain(self):
        answer = {"success": False, "message": "Only its own media answers."}
        with (
            self.get_patch_super_x(
                self.SocialPostAccountX,
                XSyncSocialPostAccount,
                "delete_comment",
                return_value=answer,
            ),
            patch.object(
                type(self.SocialAccountX), "get_client_api", autospec=True
            ) as get_client_api,
        ):
            res = self.social_post_account_id.delete_comment("777")
        self.assertEqual(res, answer)
        get_client_api.assert_not_called()
