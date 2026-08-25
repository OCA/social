# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from contextlib import contextmanager
from unittest.mock import patch

import psycopg2

from odoo.tools import mute_logger

from .test_social_advertising_common import TestSocialAdvertisingCommon


class TestSocialStage(TestSocialAdvertisingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_media_id = cls.SocialMedia.create({"name": "Other media"})
        cls.stage_active_id = cls.SocialStage.create(
            {
                "name": "Active",
                "code": "ACTIVE",
                "media_id": cls.social_media_id.id,
                "applies_to": "campaign",
                "level": "success",
            }
        )

    @contextmanager
    def _media_types(self, **media_types):
        """Give a technical ``media_type`` to the medias of the test.

        ``social.media.media_type`` is an empty selection until a connector
        module extends it, so it has to be patched to be written.

        :param media_types: media record name and the media type to write.
        """
        field = self.env["social.media"]._fields["media_type"]
        selection = [(value, value) for value in media_types.values()]
        with patch.object(field, "selection", new=selection):
            for record_name, media_type in media_types.items():
                getattr(self, record_name).write({"media_type": media_type})
            yield

    def test_default_level_is_secondary(self):
        stage = self.SocialStage.create(
            {
                "name": "Draft",
                "code": "DRAFT",
                "media_id": self.social_media_id.id,
            }
        )
        self.assertEqual(stage.level, "secondary")
        self.assertEqual(stage.applies_to, "campaign")

    def test_display_name_only_shows_the_stage_name(self):
        """The media is never part of the stage name shown to the user.

        The statusbar of a campaign already belongs to a single media, so
        repeating it on every stage only adds noise.
        """
        with self._media_types(social_media_id="linkedin"):
            self.stage_active_id.invalidate_recordset()
            self.assertEqual(self.stage_active_id.display_name, "Active")

    @mute_logger("odoo.sql_db")
    def test_code_is_unique_per_media_and_scope(self):
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                self.SocialStage.create(
                    {
                        "name": "Active duplicated",
                        "code": "ACTIVE",
                        "media_id": self.social_media_id.id,
                        "applies_to": "campaign",
                    }
                )

    def test_same_code_allowed_on_another_scope(self):
        stage = self.SocialStage.create(
            {
                "name": "Active group",
                "code": "ACTIVE",
                "media_id": self.social_media_id.id,
                "applies_to": "group",
            }
        )
        self.assertEqual(stage.applies_to, "group")
        self.assertEqual(
            self.SocialStage.search_count(
                [("code", "=", "ACTIVE"), ("media_id", "=", self.social_media_id.id)]
            ),
            2,
            msg="The same code lives once per scope of the same media.",
        )

    def test_same_code_allowed_on_another_media(self):
        stage = self.SocialStage.create(
            {
                "name": "Active other media",
                "code": "ACTIVE",
                "media_id": self.other_media_id.id,
                "applies_to": "campaign",
            }
        )
        self.assertEqual(stage.media_id, self.other_media_id)
        self.assertEqual(
            self.SocialStage.search_count(
                [
                    ("code", "=", "ACTIVE"),
                    ("applies_to", "=", "campaign"),
                    (
                        "media_id",
                        "in",
                        (self.social_media_id + self.other_media_id).ids,
                    ),
                ]
            ),
            2,
            msg="The same code lives once per media for the same scope.",
        )

    def test_get_stage_returns_the_matching_stage(self):
        with self._media_types(social_media_id="faketype"):
            stage = self.SocialStage._get_stage("faketype", "campaign", "ACTIVE")
            self.assertEqual(stage, self.stage_active_id)

    def test_get_stage_does_not_cross_scope(self):
        with self._media_types(social_media_id="faketype"):
            self.assertFalse(self.SocialStage._get_stage("faketype", "ad", "ACTIVE"))

    def test_get_stage_does_not_cross_media(self):
        self.SocialStage.create(
            {
                "name": "Active other media",
                "code": "ACTIVE",
                "media_id": self.other_media_id.id,
                "applies_to": "campaign",
            }
        )
        with self._media_types(social_media_id="faketype", other_media_id="otherfake"):
            stage = self.SocialStage._get_stage("faketype", "campaign", "ACTIVE")
            self.assertEqual(stage.media_id, self.social_media_id)

    def test_get_stage_unknown_code(self):
        with self._media_types(social_media_id="linkedin"):
            self.assertFalse(
                self.SocialStage._get_stage("linkedin", "campaign", "UNKNOWN")
            )

    def test_get_stage_without_arguments(self):
        self.assertFalse(self.SocialStage._get_stage(False, "campaign", "ACTIVE"))
        self.assertFalse(self.SocialStage._get_stage("linkedin", False, "ACTIVE"))
        self.assertFalse(self.SocialStage._get_stage("linkedin", "campaign", False))

    def test_order_by_sequence(self):
        first = self.SocialStage.create(
            {
                "name": "First",
                "code": "FIRST",
                "media_id": self.social_media_id.id,
                "sequence": 1,
            }
        )
        stages = self.SocialStage.search([("media_id", "=", self.social_media_id.id)])
        self.assertEqual(stages[0], first)
