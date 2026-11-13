# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase, tagged

from ..social_x_sync_utils import _SKIP_LIKES_CONTEXT_X
from .test_sync_x_common import TestSocialSyncCommonX

DASHBOARD_URL = "/web#action=social_media_base.social_post_account_action"


def _comment(ref, text, author_ref, liked, parent_ref=False, reply_count=0):
    """One comment shaped as ``get_comments`` answers it for X."""
    return {
        "id": ref,
        "remote_ref": ref,
        "parent_ref": parent_ref,
        "reply_count": reply_count,
        "text": text,
        "actor": "Conversation author",
        "author_ref": author_ref,
        "published_time": "1 h",
        "images_url": [],
        "liked": liked,
    }


@tagged("post_install", "-at_install")
class TestDashboardX(HttpCase, TestSocialSyncCommonX):
    """What the dashboard offers on a publication of X.

    The card draws the figures this bridge imports and offers the reaction
    and the thread it answers; the reaction is a toggle whose halves reach X
    once each, and the dialog of the thread draws and keeps the likes of the
    comments. A single tour walks all of it, so the run opens one browser.
    """

    def test_dashboard_x(self):
        publication = self.dashboard_publication(
            self.media_x_id, "X account of the tour", "X tour publication"
        )
        self.assertEqual(publication.media_type, "x")
        self.assertFalse(publication.liked_by_account)
        account_ref = publication.account_id.remote_ref
        deleted = set()
        skipped_likes = []
        reactions = []

        # ``get_comments`` and ``delete_comment`` are replaced by functions and
        # not by mocks: the dispatcher of a call from the client refuses a
        # method whose ``_api_private`` is set, and a mock answers every
        # attribute (``odoo/service/model.py``).
        def get_comments(post_account):
            skip_likes = bool(post_account.env.context.get(_SKIP_LIKES_CONTEXT_X))
            skipped_likes.append(skip_likes)
            comments = [
                _comment("x1", "Own comment", account_ref, False),
                _comment("x2", "Liked comment", "somebody_else", True),
                _comment("x3", "Plain comment", "somebody_else", False, reply_count=2),
                _comment("x4", "Liked reply", "somebody_else", True, parent_ref="x3"),
                _comment("x5", "Plain reply", "somebody_else", False, parent_ref="x3"),
            ]
            return {
                "success": True,
                "data": [
                    # A read without the likes answers none of them.
                    {**comment, "liked": comment["liked"] and not skip_likes}
                    for comment in comments
                    if comment["remote_ref"] not in deleted
                ],
            }

        def delete_comment(post_account, comment_ref):
            deleted.add(comment_ref)
            return {"success": True}

        def x_react(post_account, tweet_ref, like):
            reactions.append((tweet_ref, like))
            return like

        SocialAccount = type(self.SocialAccount)
        SocialPostAccount = type(self.SocialPostAccount)
        # The dashboard refreshes itself after every reaction, and neither
        # half of that refresh is what is under test here: both would reach X.
        self.patch(SocialAccount, "_refresh_statistics", lambda self: False)
        self.patch(
            SocialAccount,
            "_update_posts_statistics",
            lambda self, post_id, domain, imported=None: [],
        )
        self.patch(SocialPostAccount, "get_comments", get_comments)
        self.patch(SocialPostAccount, "delete_comment", delete_comment)
        self.patch(SocialPostAccount, "_x_react", x_react)
        self.start_tour(DASHBOARD_URL, "social_media_x_sync.dashboard", login="admin")
        self.assertEqual(
            reactions,
            [
                # The like of the card, then its withdrawal.
                (publication.remote_ref, True),
                (publication.remote_ref, False),
                # The likes given from the dialog.
                ("x3", True),
                ("x5", True),
            ],
        )
        self.assertFalse(publication.liked_by_account)
        self.assertEqual(deleted, {"x1"})
        self.assertEqual(
            skipped_likes[:2],
            [False, True],
            "The dialog reads the likes when it opens and not when it reloads.",
        )
