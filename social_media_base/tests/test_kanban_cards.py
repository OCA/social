# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase, tagged

from .test_social_common import TestSocialMediaBaseCommon

# A 1x1 transparent PNG: the image widget of the card loads it from the server.
PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB"
    "0C8AAAAASUVORK5CYII="
)


@tagged("post_install", "-at_install")
class TestKanbanCards(HttpCase, TestSocialMediaBaseCommon):
    """The kanban cards of the module, drawn from their ``card`` templates."""

    def test_kanban_cards(self):
        media = self.SocialMedia.create(
            {"name": "Media of the cards", "image": PNG_1X1}
        )
        publication = self.dashboard_publication(
            media, "Account of the cards", "Publication of the cards"
        )
        # Without an address the card has nothing to open on the social media.
        publication.write({"post_account_url": False})
        # A published post shows its publications in the form.
        publication.post_id.write({"state": "published"})
        Attachment = self.env["ir.attachment"]
        image = Attachment.create({"name": "image.png", "datas": PNG_1X1})
        video = Attachment.create({"name": "video.mp4", "datas": self.video_data})
        # Apart from the publication of the dashboard, whose card is clicked
        # where it would draw the images.
        medias_publication = self.SocialPostAccount.create(
            {
                "post_id": publication.post_id.id,
                "account_id": publication.account_id.id,
                "message": "Publication with medias",
                "state": "posted",
                "remote_ref": "tour-medias",
                "post_account_url": "http://testserver/tour-medias",
                "image_ids": [(6, 0, image.ids)],
                "video_ids": [(6, 0, video.ids)],
            }
        )
        campaign = self.env["utm.campaign"].create({"name": "Campaign of the cards"})
        self.SocialPost.create(
            {
                "message": "Post of the campaign",
                "account_ids": [(6, 0, publication.account_id.ids)],
                "user_id": publication.user_id.id,
                "campaign_id": campaign.id,
            }
        )
        self.start_tour(
            "/odoo/social-media", "social_media_base.kanban_cards", login="admin"
        )
        self.start_tour(
            f"/odoo/social.post.account/{medias_publication.id}",
            "social_media_base.kanban_cards_medias",
            login="admin",
        )
