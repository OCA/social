# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase, tagged

from .test_sync_linkedin_common import TestSocialSyncCommonLinkedin

DASHBOARD_URL = "/web#action=social_media_base.social_post_account_action"


@tagged("post_install", "-at_install")
class TestCardFooterLinkedin(HttpCase, TestSocialSyncCommonLinkedin):
    """What the card of a publication of LinkedIn offers.

    The three halves of the footer: this bridge imports the figures and
    answers both the reaction and the thread.
    """

    def test_card_footer_linkedin(self):
        publication = self.dashboard_publication(
            self.media_linkedin_id,
            "LinkedIn account of the tour",
            "LinkedIn tour publication",
        )
        self.assertEqual(publication.media_type, "linkedin")
        self.start_tour(
            DASHBOARD_URL, "social_media_linkedin_sync.card_footer", login="admin"
        )
