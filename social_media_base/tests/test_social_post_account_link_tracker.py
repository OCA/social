# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command

from .test_social_common import TEST_BASE_URL, TestSocialMediaBaseCommon

_URL = "https://www.binhex.cloud/"


class TestSocialPostAccountLinkTracker(TestSocialMediaBaseCommon):
    """Links published on a social media are tracked by Odoo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.User = cls.env["res.users"]
        cls.LinkTracker = cls.env["link.tracker"]
        cls.LinkTrackerClick = cls.env["link.tracker.click"]
        cls.UtmCampaign = cls.env["utm.campaign"]
        cls.utm_campaign_id = cls.UtmCampaign.create({"name": "Test Utm Campaign"})
        cls.social_post_id.campaign_id = cls.utm_campaign_id

    def _create_social_media_user(self, login):
        return self.User.create(
            {
                "name": "Social user",
                "login": login,
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "social_media_base.group_social_media_user"
                            ).id,
                        ]
                    )
                ],
            }
        )

    def _create_publication(self, message, account=None, post=None):
        return self.SocialPostAccount.create(
            {
                "post_id": (post or self.social_post_id).id,
                "account_id": (account or self.social_account_id).id,
                "message": message,
            }
        )

    def _trackers_of(self, publication):
        return self.LinkTracker.search(
            [("social_post_account_id", "=", publication.id)]
        )

    def _register_click(self, tracker, ip="127.0.0.1"):
        """Register a click without going through the controller."""
        return self.LinkTrackerClick.sudo().add_click(
            tracker.code, ip=ip, country_code=False
        )

    def test_a_message_without_a_link_is_untouched(self):
        """No link means no tracker, and no UTM source either."""
        publication = self._create_publication("No link at all")
        publication._shorten_message_links()
        self.assertEqual(publication.message, "No link at all")
        self.assertFalse(self._trackers_of(publication))
        self.assertFalse(publication.source_id)

    def test_a_message_with_a_link_is_shortened(self):
        publication = self._create_publication(f"Read it here {_URL}")
        publication._shorten_message_links()
        tracker = self._trackers_of(publication)
        self.assertEqual(len(tracker), 1)
        self.assertEqual(tracker.url, _URL)
        self.assertEqual(tracker.campaign_id, self.utm_campaign_id)
        self.assertEqual(tracker.medium_id, publication.medium_id)
        self.assertEqual(tracker.source_id, publication.source_id)
        self.assertNotIn(_URL, publication.message)
        self.assertIn(f"{TEST_BASE_URL}/r/", publication.message)

    def test_the_tracker_is_named_after_the_publication(self):
        """A title left to the core module would repeat the url of the link."""
        publication = self._create_publication(f"Read it here {_URL}")
        publication._shorten_message_links()
        tracker = self._trackers_of(publication)
        self.assertEqual(
            tracker.title,
            f"[{publication.media_id.name}] {publication.account_id.name} "
            "- Read it here",
        )
        self.assertNotEqual(tracker.title, tracker.url)

    def test_a_long_message_is_truncated_in_the_tracker_title(self):
        """Truncated like the name of the utm source, so both read alike."""
        publication = self._create_publication(
            f"A message far too long to be a title {_URL}"
        )
        publication._shorten_message_links()
        self.assertTrue(
            self._trackers_of(publication).title.endswith("A message far too lo...")
        )

    def test_a_message_made_of_a_link_only_is_named_after_its_account(self):
        """The links are dropped from the excerpt, so nothing is left of it."""
        publication = self._create_publication(_URL)
        publication._shorten_message_links()
        self.assertEqual(
            self._trackers_of(publication).title,
            f"[{publication.media_id.name}] {publication.account_id.name}",
        )

    def test_the_links_of_a_message_share_the_title_of_the_publication(self):
        """One title per publication: the url is what tells the links apart."""
        other_url = "https://odoo-community.org/"
        publication = self._create_publication(f"Read {_URL} and {other_url}")
        publication._shorten_message_links()
        trackers = self._trackers_of(publication)
        self.assertEqual(len(trackers), 2)
        self.assertEqual(len(set(trackers.mapped("title"))), 1)
        self.assertEqual(set(trackers.mapped("url")), {_URL, other_url})

    def test_two_publications_of_the_same_post_get_two_trackers(self):
        """The source of each publication is what keeps a click attributable.

        A link tracker is unique per url, campaign, medium and source, so two
        publications of the same post would otherwise share a single one.
        """
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        first = self._create_publication(f"Read it here {_URL}")
        second = self._create_publication(f"Read it here {_URL}", account=other_account)
        (first | second)._shorten_message_links()
        first_tracker = self._trackers_of(first)
        second_tracker = self._trackers_of(second)
        self.assertEqual(len(first_tracker), 1)
        self.assertEqual(len(second_tracker), 1)
        self.assertNotEqual(first_tracker, second_tracker)
        self.assertNotEqual(first_tracker.source_id, second_tracker.source_id)
        self.assertEqual(first_tracker.campaign_id, second_tracker.campaign_id)

    def test_shortening_is_idempotent(self):
        publication = self._create_publication(f"Read it here {_URL}")
        publication._shorten_message_links()
        shortened = publication.message
        publication._shorten_message_links()
        self.assertEqual(publication.message, shortened)
        self.assertEqual(len(self._trackers_of(publication)), 1)

    def test_a_publication_without_a_campaign_is_not_shortened(self):
        """Tracking is what a campaign is measured with, so it needs one."""
        post = self.SocialPost.create(
            {
                "message": f"Read it here {_URL}",
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )
        publication = self._create_publication(f"Read it here {_URL}", post=post)
        self.assertFalse(publication.campaign_id)
        publication._shorten_message_links()
        self.assertFalse(self._trackers_of(publication))
        self.assertFalse(publication.source_id)
        self.assertIn(_URL, publication.message)

    def test_link_click_count(self):
        publication = self._create_publication(f"Read it here {_URL}")
        publication._shorten_message_links()
        self.assertEqual(publication.link_click_count, 0)
        self._register_click(self._trackers_of(publication))
        publication.invalidate_recordset()
        self.utm_campaign_id.invalidate_recordset()
        self.assertEqual(publication.link_click_count, 1)
        # The native campaign counter of `link_tracker` counts it too, which
        # is what makes a social campaign behave like a mailing one.
        self.assertEqual(self.utm_campaign_id.click_count, 1)
        self.assertEqual(self.utm_campaign_id.social_click_count, 0)

    def test_the_two_click_numbers_do_not_clobber_each_other(self):
        """The figure of the social media and the one Odoo counted are apart."""
        publication = self._create_publication(f"Read it here {_URL}")
        publication._shorten_message_links()
        tracker = self._trackers_of(publication)
        self._register_click(tracker)
        self._register_click(tracker)
        # What the social media reports, written by the statistics sync.
        publication.write({"click_count": 7, "interactions_count": 7})
        publication.invalidate_recordset()
        self.assertEqual(publication.click_count, 7)
        self.assertEqual(publication.link_click_count, 2)

    def test_the_statistics_dialog_tells_the_two_click_numbers_apart(self):
        """Both counters are read there, and neither is called just Clicks."""
        view = self.env.ref(
            "social_media_base.social_post_account_view_form_statistics"
        )
        arch = self.SocialPostAccount.get_view(view.id, "form")["arch"]
        self.assertLess(
            arch.index('name="link_click_count"'),
            arch.index('name="click_count"'),
            msg="The clicks Odoo counted come before the ones of the media.",
        )
        self.assertIn("Tracked Clicks", arch)
        self.assertIn("Social Media Clicks", arch)

    def test_publishing_a_post_shortens_the_links_of_its_publications(self):
        post = self.SocialPost.create(
            {
                "message": f"Read it here {_URL}",
                "account_ids": [Command.set(self.social_account_id.ids)],
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        post.action_create_post_account()
        publication = post.post_account_ids
        self.assertIn(f"{TEST_BASE_URL}/r/", publication.message)
        self.assertNotIn(_URL, publication.message)

    def _publish_and_click(self, publication, clicks=1, first_ip=1):
        """Shorten the links of a publication and click the tracker N times."""
        publication._shorten_message_links()
        tracker = self._trackers_of(publication)
        for offset in range(clicks):
            self._register_click(tracker, ip=f"10.0.0.{first_ip + offset}")
        return tracker

    def test_link_click_count_of_a_post_sums_its_publications(self):
        other_account = self.SocialAccount.create(
            {"name": "Other account", "media_id": self.social_media_id.id}
        )
        first = self._create_publication(f"Read it here {_URL}")
        second = self._create_publication(f"Read it here {_URL}", account=other_account)
        self._publish_and_click(first, clicks=2, first_ip=1)
        self._publish_and_click(second, clicks=3, first_ip=10)
        self.social_post_id.invalidate_recordset()
        self.assertEqual(first.link_click_count, 2)
        self.assertEqual(second.link_click_count, 3)
        self.assertEqual(self.social_post_id.link_click_count, 5)

    def test_link_click_count_of_a_post_without_publications(self):
        post = self.SocialPost.create(
            {
                "message": "Still a draft",
                "account_ids": [Command.set(self.social_account_id.ids)],
            }
        )
        self.assertFalse(post.post_account_ids)
        self.assertEqual(post.link_click_count, 0)

    def test_link_click_count_of_several_posts_at_once(self):
        """The compute reads the whole recordset, not one post at a time."""
        other_post = self.SocialPost.create(
            {
                "message": "Another post",
                "account_ids": [Command.set(self.social_account_id.ids)],
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        self._publish_and_click(
            self._create_publication(f"Read it here {_URL}"), clicks=2, first_ip=1
        )
        self._publish_and_click(
            self._create_publication(f"Read it here {_URL}", post=other_post),
            clicks=1,
            first_ip=10,
        )
        posts = self.social_post_id | other_post
        posts.invalidate_recordset()
        self.assertEqual(posts.mapped("link_click_count"), [2, 1])

    def test_link_click_count_ignores_the_publications_of_another_post(self):
        other_post = self.SocialPost.create(
            {
                "message": "Another post",
                "account_ids": [Command.set(self.social_account_id.ids)],
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        self._publish_and_click(
            self._create_publication(f"Read it here {_URL}", post=other_post), clicks=4
        )
        self.social_post_id.invalidate_recordset()
        self.assertEqual(self.social_post_id.link_click_count, 0)
        self.assertEqual(other_post.link_click_count, 4)

    def test_a_click_feeds_the_post_the_campaign_and_the_native_counter(self):
        """One click, three counters, and none of them is a copy of another."""
        publication = self._create_publication(f"Read it here {_URL}")
        self._publish_and_click(publication)
        self.social_post_id.invalidate_recordset()
        self.utm_campaign_id.invalidate_recordset()
        self.assertEqual(publication.link_click_count, 1)
        self.assertEqual(self.social_post_id.link_click_count, 1)
        self.assertEqual(self.utm_campaign_id.social_link_click_count, 1)
        self.assertEqual(self.utm_campaign_id.click_count, 1)

    def test_social_link_click_count_sums_the_posts_of_the_campaign(self):
        other_post = self.SocialPost.create(
            {
                "message": "Another post",
                "account_ids": [Command.set(self.social_account_id.ids)],
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        self._publish_and_click(
            self._create_publication(f"Read it here {_URL}"), clicks=2, first_ip=1
        )
        self._publish_and_click(
            self._create_publication(f"Read it here {_URL}", post=other_post),
            clicks=3,
            first_ip=10,
        )
        self.utm_campaign_id.invalidate_recordset()
        self.assertEqual(self.utm_campaign_id.social_link_click_count, 5)

    def test_social_link_click_count_leaves_out_a_link_that_is_not_social(self):
        """A subset of the native counter, never a figure to add to it.

        A campaign tracks links that never went through a social media, and
        those must raise the native ``click_count`` and nothing else.
        """
        self._publish_and_click(self._create_publication(f"Read it here {_URL}"))
        plain_tracker = self.LinkTracker.create(
            {
                "url": "https://odoo-community.org/",
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        self.assertFalse(plain_tracker.social_post_account_id)
        self._register_click(plain_tracker, ip="10.0.0.99")
        self.utm_campaign_id.invalidate_recordset()
        self.assertEqual(self.utm_campaign_id.social_link_click_count, 1)
        self.assertEqual(self.utm_campaign_id.click_count, 2)

    def test_social_link_click_count_ignores_another_campaign(self):
        other_campaign = self.UtmCampaign.create({"name": "Another campaign"})
        other_post = self.SocialPost.create(
            {
                "message": "A post of another campaign",
                "account_ids": [Command.set(self.social_account_id.ids)],
                "campaign_id": other_campaign.id,
            }
        )
        self._publish_and_click(
            self._create_publication(f"Read it here {_URL}", post=other_post), clicks=3
        )
        (self.utm_campaign_id | other_campaign).invalidate_recordset()
        self.assertEqual(self.utm_campaign_id.social_link_click_count, 0)
        self.assertEqual(other_campaign.social_link_click_count, 3)

    def test_social_link_click_count_of_a_campaign_without_clicks(self):
        campaign = self.UtmCampaign.create({"name": "Empty campaign"})
        self.assertEqual(campaign.social_link_click_count, 0)

    def test_social_link_click_count_of_several_campaigns_at_once(self):
        other_campaign = self.UtmCampaign.create({"name": "Another campaign"})
        self._publish_and_click(self._create_publication(f"Read it here {_URL}"))
        campaigns = self.utm_campaign_id | other_campaign
        campaigns.invalidate_recordset()
        self.assertEqual(campaigns.mapped("social_link_click_count"), [1, 0])

    def test_a_social_media_user_can_publish_a_tracked_link(self):
        """`link.tracker` is read only for a plain user, an ACL row is needed."""
        user = self._create_social_media_user(login="link_tracker_user_test")
        # The publications are scoped by responsible, so the user has to own
        # the account for the test to be about the link tracker rights only.
        self.social_account_id.user_id = user
        publication = self._create_publication(f"Read it here {_URL}")
        publication.with_user(user)._shorten_message_links()
        self.assertEqual(len(self._trackers_of(publication)), 1)
