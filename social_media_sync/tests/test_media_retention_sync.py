# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, fields

from .test_social_sync_common import TestSocialMediaSyncCommon

MEDIA_MAX_AGE_PARAM = "social_media_sync.media_max_age_days"


class TestMediaRetentionParameterSync(TestSocialMediaSyncCommon):
    """The system parameter that puts a maximum age on the downloaded medias."""

    def test_the_parameter_ships_as_no_retention(self):
        """The module writes the parameter so that it can be found, at zero.

        Zero is no policy at all, which is what an installation gets until an
        administrator puts a number in it.
        """
        self.assertEqual(
            self.env["ir.config_parameter"].sudo().get_param(MEDIA_MAX_AGE_PARAM),
            "0",
        )
        self.assertEqual(self.SocialPostAccount._media_retention_days(), 0)

    def test_the_parameter_is_read_as_an_integer(self):
        """A system parameter is text, and the policy needs a number of days."""
        self.env["ir.config_parameter"].sudo().set_param(MEDIA_MAX_AGE_PARAM, "30")
        self.assertEqual(self.SocialPostAccount._media_retention_days(), 30)

    def test_a_parameter_that_is_not_a_number_is_no_retention(self):
        """What cannot be read as a number is read as no policy, not as a crash."""
        self.env["ir.config_parameter"].sudo().set_param(
            MEDIA_MAX_AGE_PARAM, "every other tuesday"
        )
        self.assertEqual(self.SocialPostAccount._media_retention_days(), 0)

    def test_a_negative_parameter_is_no_retention(self):
        """A negative age releases nothing, the same as no policy at all."""
        self.env["ir.config_parameter"].sudo().set_param(MEDIA_MAX_AGE_PARAM, "-30")
        self.assertEqual(self.SocialPostAccount._media_retention_days(), -30)
        post_account, attachments = self._imported_publication_for_parameter()
        self.SocialPostAccount._gc_aged_post_medias()
        self.assertEqual(post_account.image_ids, attachments)

    def _imported_publication_for_parameter(self):
        """An imported publication old enough for any policy."""
        post_account = self.SocialPostAccount.create(
            {
                "message": "Imported long ago",
                "account_id": self.social_account_id.id,
                "state": "posted",
                "published_date": fields.Datetime.subtract(
                    fields.Datetime.now(), days=600
                ),
            }
        )
        image = self.env["ir.attachment"].create(
            {"name": "media.png", "type": "binary", "datas": b"aW1n"}
        )
        post_account.write({"image_ids": [Command.link(image.id)]})
        return post_account, image


class TestMediaRetentionSync(TestSocialMediaSyncCommon):
    """The pass that ages out the medias downloaded from the social media."""

    def _set_max_age(self, value):
        """Write the retention parameter as an administrator would."""
        self.env["ir.config_parameter"].sudo().set_param(MEDIA_MAX_AGE_PARAM, value)

    def _imported_publication(self, days_ago, images=1):
        """Create an imported publication holding downloaded medias.

        Imported is what has no post: the fan-out of a post never gets here,
        which is what the domain of the policy asks for.

        :return: the publication and the attachments it downloaded.
        :rtype: tuple
        """
        post_account = self.SocialPostAccount.create(
            {
                "message": f"Imported {days_ago} days ago",
                "account_id": self.social_account_id.id,
                "state": "posted",
                "published_date": fields.Datetime.subtract(
                    fields.Datetime.now(), days=days_ago
                ),
            }
        )
        attachments = self.env["ir.attachment"].create(
            [
                {"name": f"media_{index}.png", "type": "binary", "datas": b"aW1n"}
                for index in range(images)
            ]
        )
        post_account.write(
            {"image_ids": [Command.link(media.id) for media in attachments]}
        )
        post_account.media_refs = {
            str(media.id): f"urn:li:image:{media.id}" for media in attachments
        }
        return post_account, attachments

    def _age_attachments(self, attachments, days=2):
        """Move the dates of the attachments back, as the vacuum reads them."""
        older = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        # The dates are written in SQL, so what the ORM still holds for these
        # attachments has to reach the database first and be forgotten after,
        # or the next flush would write ``write_date`` back to now.
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_attachment SET create_date = %s, write_date = %s "
            "WHERE id IN %s",
            (older, older, tuple(attachments.ids)),
        )
        attachments.invalidate_recordset(["create_date", "write_date"])

    def test_the_pass_does_nothing_without_a_parameter(self):
        """No policy written is no media released, whatever the age."""
        self._set_max_age("")
        post_account, attachments = self._imported_publication(days_ago=600)
        self.SocialPostAccount._gc_aged_post_medias()
        self.assertEqual(post_account.image_ids, attachments)

    def test_the_pass_does_nothing_with_a_value_that_is_not_a_number(self):
        """A parameter written by hand is read as no policy, not as a crash."""
        self._set_max_age("every other tuesday")
        post_account, attachments = self._imported_publication(days_ago=600)
        self.assertEqual(self.SocialPostAccount._media_retention_days(), 0)
        self.SocialPostAccount._gc_aged_post_medias()
        self.assertEqual(post_account.image_ids, attachments)

    def test_the_pass_releases_the_medias_older_than_the_policy(self):
        """The publication loses its medias and keeps every reference."""
        self._set_max_age("30")
        old, old_medias = self._imported_publication(days_ago=60)
        recent, recent_medias = self._imported_publication(days_ago=10)
        expected_refs = dict(old.media_refs)
        self.SocialPostAccount._gc_aged_post_medias()
        self.assertFalse(old.image_ids)
        self.assertFalse(old.video_ids)
        old.invalidate_recordset(["media_refs"])
        self.assertEqual(old.media_refs, expected_refs)
        self.assertEqual(recent.image_ids, recent_medias)
        self.assertTrue(old_medias.sudo().exists())

    def test_the_medias_of_a_post_are_never_released(self):
        """Editorial content is not aged out, whatever the age of the post."""
        self._set_max_age("30")
        image = self.env["ir.attachment"].create(
            {"name": "editorial.png", "type": "binary", "datas": b"aW1n"}
        )
        post = self.SocialPost.create(
            {
                "message": "Published from Odoo a long time ago",
                "account_ids": [Command.link(self.social_account_id.id)],
                "image_ids": [Command.link(image.id)],
            }
        )
        publication = self.SocialPostAccount.create(
            {
                "post_id": post.id,
                "account_id": self.social_account_id.id,
                "message": post.message,
                "state": "posted",
                "published_date": fields.Datetime.subtract(
                    fields.Datetime.now(), days=600
                ),
                "image_ids": [Command.link(image.id)],
            }
        )
        self.SocialPostAccount._gc_aged_post_medias()
        self.assertEqual(publication.image_ids, image)
        self.assertEqual(post.image_ids, image)

    def test_the_released_media_is_not_downloaded_again(self):
        """``media_refs`` still answers for the media the publication had."""
        self._set_max_age("30")
        post_account, attachments = self._imported_publication(days_ago=60)
        references = list(post_account.media_refs.values())
        self.SocialPostAccount._gc_aged_post_medias()
        self.assertFalse(post_account.image_ids)
        self.assertEqual(post_account._get_medias_account(references), references)
        self.assertTrue(attachments)

    def test_the_released_attachment_waits_a_day_for_the_vacuum(self):
        """Releasing leaves the file recoverable until the next vacuum."""
        self._set_max_age("30")
        post_account, attachments = self._imported_publication(days_ago=60)
        self.SocialPostAccount._gc_aged_post_medias()
        self.assertEqual(attachments.sudo().mapped("res_id"), [0])
        self.SocialPostAccount._gc_lost_media_attachments()
        self.assertTrue(attachments.sudo().exists())
        self._age_attachments(attachments)
        self.SocialPostAccount._gc_lost_media_attachments()
        self.assertFalse(attachments.sudo().exists())

    def test_the_pass_stops_at_the_limit(self):
        """One pass reaches as many publications as it was given, no more."""
        self._set_max_age("30")
        publications = [self._imported_publication(days_ago=60) for _ in range(3)]
        self.SocialPostAccount._gc_aged_post_medias(limit=2)
        untouched = [
            post_account
            for post_account, medias in publications
            if post_account.image_ids == medias
        ]
        self.assertEqual(len(untouched), 1)
