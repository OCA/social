# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase, tagged

from .test_sync_x_common import TestSocialSyncCommonX

DASHBOARD_URL = "/web#action=social_media_base.social_post_account_action"


@tagged("post_install", "-at_install")
class TestCardFooterX(HttpCase, TestSocialSyncCommonX):
    """What the card of a publication of X offers.

    The figures and the thread, because this bridge imports the first and
    answers the second, and no reaction, because X serves none.
    """

    def test_card_footer_x(self):
        publication = self.dashboard_publication(
            self.media_x_id, "X account of the tour", "X tour publication"
        )
        self.assertEqual(publication.media_type, "x")
        self.start_tour(DASHBOARD_URL, "social_media_x_sync.card_footer", login="admin")
