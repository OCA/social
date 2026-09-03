# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError

from .test_social_common import TestSocialMediaBaseCommon


class TestSocialPostAccountUtm(TestSocialMediaBaseCommon):
    """The UTM medium and source reported for a publication."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.UtmMedium = cls.env["utm.medium"]
        cls.utm_medium_social_media = cls.env.ref(
            "social_media_base.utm_medium_social_media"
        )

    def test_medium_defaults_to_the_generic_social_media_medium(self):
        """A social media without a medium of its own reports the generic one."""
        self.assertEqual(
            self.social_post_account_id.medium_id, self.utm_medium_social_media
        )

    def test_medium_comes_from_the_media_when_configured(self):
        medium = self.UtmMedium.create({"name": "Configured medium"})
        self.social_media_id.utm_medium_id = medium
        self.social_post_account_id.invalidate_recordset()
        self.assertEqual(self.social_post_account_id.medium_id, medium)

    def test_medium_is_writable(self):
        """The computed medium is only a default, it can be overridden."""
        medium = self.UtmMedium.create({"name": "Hand picked medium"})
        self.social_post_account_id.medium_id = medium
        self.assertEqual(self.social_post_account_id.medium_id, medium)

    def test_source_is_empty_until_it_is_needed(self):
        self.assertFalse(self.social_post_account_id.source_id)

    def test_ensure_utm_source_is_idempotent(self):
        self.social_post_account_id._ensure_utm_source()
        source = self.social_post_account_id.source_id
        self.assertTrue(source)
        self.social_post_account_id._ensure_utm_source()
        self.assertEqual(self.social_post_account_id.source_id, source)

    def test_two_publications_of_the_same_post_get_two_sources(self):
        """Each publication owns its source, which is what makes a click attributable.

        A link tracker is unique per url, campaign, medium and source, so two
        publications sharing a source would share a single tracker.
        """
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        other_publication = self.SocialPostAccount.create(
            {
                "post_id": self.social_post_id.id,
                "account_id": other_account.id,
                "message": self.social_post_account_id.message,
            }
        )
        publications = self.social_post_account_id | other_publication
        publications._ensure_utm_source()
        self.assertEqual(len(publications.source_id), 2)

    def test_deleting_the_generic_medium_raises(self):
        with self.assertRaises(UserError):
            self.utm_medium_social_media.unlink()
