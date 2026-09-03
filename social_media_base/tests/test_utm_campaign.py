# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

from .test_social_common import TestSocialMediaBaseCommon


class TestUtmCampaign(TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.User = cls.env["res.users"]
        cls.UtmCampaign = cls.env["utm.campaign"]
        cls.utm_campaign_id = cls.UtmCampaign.create({"name": "Test campaign"})
        # The campaign is set on the post, which is the only supported way:
        # a publication of a post carries the campaign of that post.
        cls.social_post_id.campaign_id = cls.utm_campaign_id

    def _create_imported_publication(self, **values):
        """Return a publication without a parent post, as the connectors import them."""
        return self.SocialPostAccount.create(
            dict(
                {
                    "account_id": self.social_account_id.id,
                    "message": "Imported from the wall",
                },
                **values,
            )
        )

    def test_the_new_post_action_carries_the_campaign(self):
        """The header button opens a post already attached to the campaign."""
        action = self.env.ref("social_media_base.social_post_action_from_campaign")
        self.assertEqual(action.res_model, "social.post")
        # The form comes first: the button creates a post, it does not list them.
        self.assertTrue(action.view_mode.startswith("form"))
        evaluated = safe_eval(
            action.context,
            {"active_id": self.utm_campaign_id.id, "uid": self.env.uid},
        )
        self.assertEqual(evaluated["default_campaign_id"], self.utm_campaign_id.id)
        self.assertEqual(
            evaluated["search_default_campaign_id"], [self.utm_campaign_id.id]
        )
        self.assertEqual(evaluated["default_user_id"], self.env.uid)

    def test_social_post_ids_holds_the_posts_of_the_campaign(self):
        self.assertIn(self.social_post_id, self.utm_campaign_id.social_post_ids)

    def test_social_post_ids_shows_a_post_that_was_never_published(self):
        """The point of the field: a campaign shows the work already planned.

        The publications of a post are not created until it is published, so
        until this field existed a campaign of drafts looked empty.
        """
        post = self.SocialPost.create(
            {
                "message": "Still a draft",
                "account_ids": [Command.set([self.social_account_id.id])],
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        self.assertEqual(post.state, "draft")
        self.assertFalse(post.post_account_ids)
        self.utm_campaign_id.invalidate_recordset()
        self.assertIn(post, self.utm_campaign_id.social_post_ids)

    def test_social_post_ids_is_not_filtered_by_state(self):
        """Every state shows, like ``mailing_mail_ids`` of ``mass_mailing``."""
        published = self.SocialPost.create(
            {
                "message": "A published post",
                "account_ids": [Command.set([self.social_account_id.id])],
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        published.state = "published"
        cancelled = self.SocialPost.create(
            {
                "message": "A cancelled post",
                "account_ids": [Command.set([self.social_account_id.id])],
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        cancelled.state = "cancelled"
        self.utm_campaign_id.invalidate_recordset()
        self.assertLessEqual(
            {published, cancelled, self.social_post_id},
            set(self.utm_campaign_id.social_post_ids),
        )

    def test_social_post_ids_ignores_the_posts_of_another_campaign(self):
        other_campaign = self.UtmCampaign.create({"name": "Another campaign"})
        other_post = self.SocialPost.create(
            {
                "message": "A post of another campaign",
                "account_ids": [Command.set([self.social_account_id.id])],
                "campaign_id": other_campaign.id,
            }
        )
        self.assertNotIn(other_post, self.utm_campaign_id.social_post_ids)
        self.assertIn(other_post, other_campaign.social_post_ids)

    def test_social_post_count(self):
        self.assertEqual(self.utm_campaign_id.social_post_count, 1)
        self.SocialPost.create(
            {
                "message": "A second post",
                "account_ids": [Command.set([self.social_account_id.id])],
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        self.utm_campaign_id.invalidate_recordset()
        self.assertEqual(self.utm_campaign_id.social_post_count, 2)

    def test_social_post_count_counts_a_draft_post(self):
        """The stat button of the campaign shows up before anything is posted."""
        campaign = self.UtmCampaign.create({"name": "Campaign of drafts"})
        self.SocialPost.create(
            {
                "message": "Still a draft",
                "account_ids": [Command.set([self.social_account_id.id])],
                "campaign_id": campaign.id,
            }
        )
        self.assertEqual(campaign.social_post_count, 1)

    def test_social_post_count_of_a_campaign_without_posts(self):
        campaign = self.UtmCampaign.create({"name": "Empty campaign"})
        self.assertEqual(campaign.social_post_count, 0)

    def test_social_post_count_of_a_campaign_being_edited(self):
        """A campaign in the form is a virtual record standing for a real one."""
        virtual = self.UtmCampaign.new({"name": "Virtual"}, origin=self.utm_campaign_id)
        self.assertEqual(virtual.social_post_count, 1)

    def test_action_view_social_posts(self):
        action = self.utm_campaign_id.action_view_social_posts()
        self.assertEqual(action["res_model"], "social.post")
        self.assertEqual(
            action["domain"], [("campaign_id", "=", self.utm_campaign_id.id)]
        )
        self.assertEqual(
            action["context"]["default_campaign_id"], self.utm_campaign_id.id
        )

    def test_action_view_social_posts_finds_the_posts_of_the_campaign(self):
        """The domain of the action and the O2m answer the same thing."""
        action = self.utm_campaign_id.action_view_social_posts()
        self.assertEqual(
            self.SocialPost.search(action["domain"]),
            self.utm_campaign_id.social_post_ids,
        )

    def test_the_posts_of_a_campaign_are_readonly(self):
        field = self.UtmCampaign.fields_get(["social_post_ids"])
        self.assertTrue(field["social_post_ids"]["readonly"])

    def test_social_post_account_ids_holds_the_publications_of_the_campaign(self):
        self.assertIn(
            self.social_post_account_id, self.utm_campaign_id.social_post_account_ids
        )

    def test_unlinking_an_imported_publication_only_clears_its_campaign(self):
        """Removing a line from the campaign keeps the publication alive."""
        publication = self._create_imported_publication(
            campaign_id=self.utm_campaign_id.id
        )
        self.assertFalse(publication.post_id)
        self.utm_campaign_id.write(
            {"social_post_account_ids": [Command.unlink(publication.id)]}
        )
        self.assertTrue(publication.exists())
        self.assertFalse(publication.campaign_id)

    def test_linking_an_imported_publication_sets_its_campaign(self):
        publication = self._create_imported_publication()
        self.assertFalse(publication.post_id)
        self.utm_campaign_id.write(
            {"social_post_account_ids": [Command.link(publication.id)]}
        )
        self.assertEqual(publication.campaign_id, self.utm_campaign_id)

    def test_a_publication_cannot_leave_the_campaign_of_its_post(self):
        with self.assertRaises(ValidationError):
            self.social_post_account_id.campaign_id = False

    def test_a_publication_cannot_take_another_campaign_than_its_post(self):
        other_campaign = self.UtmCampaign.create({"name": "Another campaign"})
        with self.assertRaises(ValidationError):
            self.social_post_account_id.campaign_id = other_campaign

    def test_an_imported_publication_keeps_its_campaign_after_invalidation(self):
        """A campaign written on a publication without a post is never wiped.

        This is the reason ``campaign_id`` is a computed field and not a
        related one: a related traverses ``post_id`` unconditionally and would
        clear the campaign of every imported publication.
        """
        publication = self._create_imported_publication(
            campaign_id=self.utm_campaign_id.id
        )
        publication.invalidate_recordset()
        self.assertEqual(publication.campaign_id, self.utm_campaign_id)

    def test_adopting_an_imported_publication_takes_the_campaign_of_the_post(self):
        """Giving a parent post to an imported publication resynchronizes it.

        Writing ``post_id`` triggers the compute, so the publication takes the
        campaign of its new post instead of violating the constraint.
        """
        other_campaign = self.UtmCampaign.create({"name": "Another campaign"})
        publication = self._create_imported_publication(campaign_id=other_campaign.id)
        publication.post_id = self.social_post_id
        self.assertEqual(publication.campaign_id, self.utm_campaign_id)

    def test_publishing_a_post_propagates_its_campaign(self):
        """The fan-out creates the lines without a campaign and recomputes it."""
        post = self.SocialPost.create(
            {
                "message": "A post of the campaign",
                "account_ids": [Command.set([self.social_account_id.id])],
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        post.action_create_post_account()
        self.assertTrue(post.post_account_ids)
        self.assertEqual(post.post_account_ids.campaign_id, self.utm_campaign_id)

    def test_the_publications_of_a_campaign_are_readonly(self):
        field = self.UtmCampaign.fields_get(["social_post_account_ids"])
        self.assertTrue(field["social_post_account_ids"]["readonly"])

    def _set_statistics(self, publication, **values):
        publication.write(
            dict(
                {
                    "click_count": 0,
                    "like_count": 0,
                    "comment_count": 0,
                    "share_count": 0,
                    "impression_count": 0.0,
                    "engagement": 0.0,
                },
                **values,
            )
        )

    def test_social_statistics(self):
        self._set_statistics(
            self.social_post_account_id,
            click_count=3,
            like_count=5,
            comment_count=1,
            share_count=2,
            impression_count=100.0,
            engagement=0.2,
        )
        self._set_statistics(
            self._create_imported_publication(campaign_id=self.utm_campaign_id.id),
            click_count=7,
            like_count=1,
            comment_count=4,
            share_count=0,
            impression_count=50.0,
            engagement=0.4,
        )
        self.utm_campaign_id.invalidate_recordset()
        self.assertEqual(self.utm_campaign_id.social_click_count, 10)
        self.assertEqual(self.utm_campaign_id.social_like_count, 6)
        self.assertEqual(self.utm_campaign_id.social_comment_count, 5)
        self.assertEqual(self.utm_campaign_id.social_share_count, 2)
        self.assertEqual(self.utm_campaign_id.social_impression_count, 150.0)
        # 3 + 5 + 1 + 2 and 7 + 1 + 4 + 0
        self.assertEqual(self.utm_campaign_id.social_interactions_count, 23)
        # Added up, not averaged: the campaign totals the engagement of its
        # publications, the same way the card of a post totals its own.
        self.assertAlmostEqual(self.utm_campaign_id.social_engagement, 0.6)

    def test_social_engagement_is_a_total_and_not_an_average(self):
        """Enough publications that a sum and an average cannot be confused."""
        for engagement in (1.0, 2.0, 3.0):
            self._set_statistics(
                self._create_imported_publication(campaign_id=self.utm_campaign_id.id),
                engagement=engagement,
            )
        self._set_statistics(self.social_post_account_id, engagement=0.0)
        self.utm_campaign_id.invalidate_recordset()
        self.assertAlmostEqual(self.utm_campaign_id.social_engagement, 6.0)

    def test_social_statistics_of_a_campaign_without_publications(self):
        campaign = self.UtmCampaign.create({"name": "Empty campaign"})
        self.assertEqual(campaign.social_click_count, 0)
        self.assertEqual(campaign.social_like_count, 0)
        self.assertEqual(campaign.social_comment_count, 0)
        self.assertEqual(campaign.social_share_count, 0)
        self.assertEqual(campaign.social_impression_count, 0.0)
        self.assertEqual(campaign.social_interactions_count, 0)
        self.assertEqual(campaign.social_engagement, 0.0)

    def test_social_statistics_ignore_the_publications_of_another_campaign(self):
        other_campaign = self.UtmCampaign.create({"name": "Another campaign"})
        self._set_statistics(
            self._create_imported_publication(campaign_id=other_campaign.id),
            click_count=9,
        )
        self._set_statistics(self.social_post_account_id, click_count=2)
        self.utm_campaign_id.invalidate_recordset()
        self.assertEqual(self.utm_campaign_id.social_click_count, 2)
        self.assertEqual(other_campaign.social_click_count, 9)

    def test_the_publications_are_hidden_without_the_social_group(self):
        """A plain user of the marketing campaigns reads no social data."""
        user = self.User.create(
            {
                "name": "Marketing user",
                "login": "marketing_user_test",
                "groups_id": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        fields_get = self.UtmCampaign.with_user(user).fields_get()
        self.assertNotIn("social_post_ids", fields_get)
        self.assertNotIn("social_post_count", fields_get)
        self.assertNotIn("social_link_click_count", fields_get)
        self.assertNotIn("social_post_account_ids", fields_get)
        self.assertNotIn("social_click_count", fields_get)


class TestSocialPostCampaign(TestSocialMediaBaseCommon):
    """The marketing campaign a post carries and hands to its publications."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.UtmCampaign = cls.env["utm.campaign"]
        cls.utm_campaign_id = cls.UtmCampaign.create({"name": "Test campaign"})

    def test_campaign_id_follows_the_parent_post(self):
        self.social_post_id.campaign_id = self.utm_campaign_id
        self.assertEqual(self.social_post_account_id.campaign_id, self.utm_campaign_id)
        self.social_post_id.campaign_id = False
        self.assertFalse(self.social_post_account_id.campaign_id)

    def test_the_campaign_of_an_imported_publication_is_kept(self):
        """A publication without parent post keeps the campaign written on it."""
        imported = self.SocialPostAccount.create(
            {
                "account_id": self.social_account_id.id,
                "message": "Imported from the wall",
                "remote_ref": "urn:remote:1",
            }
        )
        imported.campaign_id = self.utm_campaign_id
        imported.write({"like_count": 5})
        imported.invalidate_recordset()
        self.assertEqual(imported.campaign_id, self.utm_campaign_id)

    def test_get_locked_content_fields_freezes_the_campaign(self):
        self.assertIn("campaign_id", self.social_post_id._get_locked_content_fields())

    def test_the_campaign_of_a_published_post_cannot_be_changed(self):
        self.social_post_account_id.write(
            {"state": "posted", "remote_ref": "urn:posted"}
        )
        self.assertTrue(self.social_post_id.content_locked)
        with self.assertRaises(UserError):
            self.social_post_id.write({"campaign_id": self.utm_campaign_id.id})
        self.assertFalse(self.social_post_id.campaign_id)
