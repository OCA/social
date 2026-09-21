# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import HttpCase, tagged

from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
)

from .test_sync_linkedin_common import (
    PATCH_SYNC_ACCOUNT_LINKEDIN,
    PATCH_SYNC_POST_ACCOUNT_LINKEDIN,
    TestSocialSyncCommonLinkedin,
)

DASHBOARD_URL = "/web#action=social_media_base.social_post_account_action"


def _comment(ref, text, parent_ref=False):
    """One comment shaped as ``get_comments`` answers it.

    ``reply_count`` is left unset, which is what a social media that does not
    count the replies answers, and the replies travel with the comments: the
    branch unfolds from what the dialog already holds.
    """
    return {
        "id": ref,
        "remote_ref": ref,
        "parent_ref": parent_ref,
        "reply_count": None,
        "text": text,
        "actor": "Conversation author",
        "published_time": "1 h",
        "images_url": [],
        "liked": False,
    }


# The order is the one the social media answered, and it is the order the
# dialog has to draw: two roots, a reply, a reply of that reply, and a pair of
# comments pointing at each other.
CONVERSATION = [
    _comment("c1", "Root one"),
    _comment("c2", "Reply to one", parent_ref="c1"),
    _comment("c3", "Root two"),
    _comment("c4", "Reply of the reply", parent_ref="c2"),
    _comment("c5", "Cycle A", parent_ref="c6"),
    _comment("c6", "Cycle B", parent_ref="c5"),
]


@tagged("post_install", "-at_install")
class TestCommentDialogLinkedin(HttpCase, TestSocialSyncCommonLinkedin):
    """What the comment dialog of ``social_media_sync`` draws.

    The dialog and its tour belong to ``social_media_sync``, but only a bridge
    answers a thread, so the run happens here: the entry that opens the dialog
    is offered by the social media this bridge serves.
    """

    def test_comment_dialog_draws_the_conversation(self):
        publication = self.dashboard_publication(
            self.media_linkedin_id,
            "LinkedIn account of the conversation",
            "Conversation publication",
        )
        self.assertEqual(publication.media_type, "linkedin")
        # Neither the figures of the dashboard nor the import are what the
        # tour is about, and both would reach LinkedIn.
        #
        # ``get_comments`` is replaced by a function and not by a mock: the
        # dispatcher of a call from the client refuses a method whose
        # ``_api_private`` is set, and a mock answers every attribute
        # (``odoo/service/model.py``).
        with patch(
            PATCH_ACCOUNT_LINKEDIN.format("_refresh_statistics"),
            return_value=False,
        ), patch(
            PATCH_SYNC_ACCOUNT_LINKEDIN.format("_update_posts_statistics"),
            return_value=[],
        ), patch(
            PATCH_SYNC_POST_ACCOUNT_LINKEDIN.format("get_comments"),
            lambda post_account: {"success": True, "data": CONVERSATION},
        ):
            self.start_tour(
                DASHBOARD_URL, "social_media_sync.comment_dialog", login="admin"
            )
