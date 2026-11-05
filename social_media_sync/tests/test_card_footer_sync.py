# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase, tagged

from .test_social_sync_common import TestSocialMediaSyncCommon

DASHBOARD_URL = "/web#action=social_media_base.social_post_account_action"
# The social media of the test, which no bridge answers for. A value of its
# own instead of one of the installed connectors, because every connector
# installed in the database that runs this brings its bridge with it.
MEDIA_TYPE_WITHOUT_BRIDGE = "nobridge"


@tagged("post_install", "-at_install")
class TestCardFooterWithoutBridge(HttpCase, TestSocialMediaSyncCommon):
    """What the card of a publication no bridge serves offers: nothing.

    This module holds the thread and the reactions, but what answers them for
    a given social media is its bridge, and the figures are imported by the
    bridge too. A social media with none is what an installation without that
    bridge looks like, and the footer says none of the three.
    """

    def test_card_footer_without_bridge(self):
        media = self.SocialMedia.create({"name": "Social media without bridge"})
        with self._fake_media_types(**{MEDIA_TYPE_WITHOUT_BRIDGE: media}):
            publication = self.dashboard_publication(
                media, "Account without bridge", "Publication without bridge"
            )
            self.assertEqual(publication.media_type, MEDIA_TYPE_WITHOUT_BRIDGE)
            self.start_tour(
                DASHBOARD_URL, "social_media_sync.card_footer", login="admin"
            )
