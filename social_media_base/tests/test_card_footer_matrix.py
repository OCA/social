# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase, tagged

from .test_social_common import TestSocialMediaBaseCommon

DASHBOARD_URL = "/web#action=social_media_base.social_post_account_action"


# ``post_install`` like every test of the family: an ``at_install`` test runs
# before the connectors are loaded, and there the social media of a connector
# is not even a legal value of the selection yet.
@tagged("post_install", "-at_install", "-standard", "card_footer_matrix")
class TestCardFooterMatrix(HttpCase, TestSocialMediaBaseCommon):
    """The footer of the card in an installation that imports nothing.

    Out of the standard suite on purpose: what it asserts is what an
    installation *without* a synchronization module draws, and the suite runs
    with every module of the repository installed. It is run against the
    databases of the install matrix::

        odoo -d <database> --test-enable --stop-after-init --workers=0 \\
            -u social_media_base --test-tags card_footer_matrix
    """

    def _matrix_media(self):
        """The social media of a connector, or the one of the fixtures.

        A database of the matrix has the connector installed and its bridge
        not, so the publication is of a social media a bridge could serve;
        when there is no connector at all, the media of the fixtures does.
        """
        media = self.SocialMedia.search([("media_type", "!=", False)], limit=1)
        return media or self.social_media_id

    def test_card_footer_says_nothing(self):
        self.dashboard_publication(
            self._matrix_media(),
            "Account of the matrix",
            "Publication of the matrix",
        )
        self.start_tour(
            DASHBOARD_URL, "social_media_base.card_footer_matrix", login="admin"
        )
