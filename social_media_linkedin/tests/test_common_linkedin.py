# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


import base64
from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.fields import Command

from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

from ..social_linkedin_utils import social_url_encode

PATCH_WIZARD_LINKEDIN = "odoo.addons.social_media_linkedin.wizards.{}"
PATCH_WIZARD_ACCOUNT_LINKEDIN = PATCH_WIZARD_LINKEDIN.format("wizard_social_account.{}")

PATCH_ACCOUNT_LINKEDIN = (
    "odoo.addons.social_media_linkedin.models.social_account.SocialAccount.{}"
)
PATCH_POST_ACCOUNT_LINKEDIN = (
    "odoo.addons.social_media_linkedin.models."
    "social_post_account.SocialPostAccount.{}"
)


def _linkedin_day(offset):
    """Return the ISO day ``offset`` days back from today.

    The check trims the buckets to ``_linkedin_check_days``, so the fixtures
    move with the calendar instead of naming a fixed day that would fall out
    of the window as soon as it went past.
    """
    return (fields.Date.today() - timedelta(days=offset)).isoformat()


def _linkedin_buckets(statistics):
    """Return the watched figures as the buckets the finder answers.

    ``_get_linkedin_daily_statistics`` builds six figures per day and the
    check keeps five. The engagement is put back as a ratio of its own, so a
    figure leaking through would be caught by its value.
    """
    return {
        day: (clicks, likes, comments, shares, 0.5, impressions)
        for day, (
            clicks,
            likes,
            comments,
            shares,
            impressions,
        ) in statistics.items()
    }


RECENT_STATISTICS_LINKEDIN = {
    _linkedin_day(3): (0, 0, 0, 0, 17),
    _linkedin_day(2): (5, 0, 0, 0, 29),
    _linkedin_day(1): (0, 1, 0, 0, 0),
}


class LinkedinMockMixin:
    def _mock_linkedin(self, return_value, account, attribute="_request_linkedin"):
        return patch.object(type(account), attribute, return_value=return_value)


class TestSocialCommonLinkedin(LinkedinMockMixin, TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.VALID_PNG_B64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQYV2NgYGBgAAAA"
            "BAABJzQnCgAAAABJRU5ErkJggg=="
        )
        cls.WizardAccount = cls.env["wizard.social.account"]
        cls.wizard_account_id = cls.WizardAccount.create(
            {
                "media_id": cls.env.ref(
                    "social_media_linkedin.social_media_linkedin"
                ).id,
                "csrf_state_token": "fake-csrf-token",
                "linkedin_client": "fake-client-id",
                "linkedin_secret": "fake-secret",
            }
        )
        cls.url_callback = f"{cls.wizard_account_id.get_base_url()}/linkedin/callback"
        cls.media_linkedin_id = cls.SocialMedia.create(
            {
                "name": "linkedin",
                "media_type": "linkedin",
            }
        )

        cls.SocialAccountLinkedin = cls.SocialAccount.create(
            {
                "name": "Linkedin Account",
                "media_id": cls.media_linkedin_id.id,
                "remote_ref": "urn:li:organization:123456",
                "access_token": "fake-token",
                "linkedin_client_id": "fake-client-id",
                "linkedin_secret": "fake-secret",
            }
        )

        cls.SocialAccountLinkedinData = cls.SocialAccount.create(
            {
                "name": "Linkedin Account",
                "media_id": cls.env.ref(
                    "social_media_linkedin.social_media_linkedin"
                ).id,
                "remote_ref": "urn:li:organization:123456890",
                "access_token": "fake-token",
            }
        )

        cls.SocialPostLinkedin = cls.SocialPost.create(
            {
                "message": "Test Message",
                "account_ids": [Command.set(cls.SocialAccountLinkedin.ids)],
            }
        )

        post_account = {
            "message": "Test Message",
            "account_id": cls.SocialAccountLinkedin.id,
            "media_id": cls.media_linkedin_id.id,
            "post_id": cls.SocialPostLinkedin.id,
            "remote_ref": "1234567890",
            "state": "posted",
        }

        cls.SocialPostAccountLinkedin = cls.SocialPostAccount.create(post_account)

        post_account.update(
            {
                "state": "ready",
                "remote_ref": False,
            }
        )
        cls.SocialPostAccountReadyLinkedin = cls.SocialPostAccount.create(post_account)

    def create_attachment(self, attach_name="test_exist_image.jpg", size=None):
        """Create an attachment of a given name, and optionally of a size.

        The mimetype is guessed from the name by ``ir.attachment`` itself, and
        the size is the length of the content, so a test about a limit has to
        write the bytes: ``file_size`` is dropped from the values on write.

        :param str attach_name: name of the file, which decides its mimetype.
        :param int size: number of bytes the attachment weighs.
        :rtype: odoo.api.Model
        """
        content = b"\0" * size if size else b"existing"
        return self.env["ir.attachment"].create(
            {
                "name": attach_name,
                "type": "binary",
                "datas": base64.b64encode(content).decode(),
                "res_model": "social.post.account",
                "res_id": self.SocialPostAccountLinkedin.id,
            }
        )

    def get_patch_exceptions_linkedin(self, fake_client=False, side_effect=False):
        if side_effect:
            return patch.object(
                type(self.SocialAccountLinkedin),
                "_request_linkedin",
                autospec=True,
                side_effect=side_effect,
            )
        return patch.object(
            type(self.SocialAccountLinkedin),
            "_request_linkedin",
            autospec=True,
            return_value=fake_client,
        )

    def _isolate_linkedin_account(self):
        """Leave ``SocialAccountLinkedin`` as the only LinkedIn account.

        ``_run_check_media_updates`` scans every LinkedIn account, so the
        other accounts have to be archived to know which one the assertions
        are about.
        """
        self.SocialAccount.search(
            [
                ("media_type", "=", "linkedin"),
                ("id", "!=", self.SocialAccountLinkedin.id),
            ]
        ).write({"active": False})

    def _patch_reader(self, buckets=None, side_effect=None):
        """Answer the daily finder without reaching LinkedIn."""
        return patch(
            PATCH_ACCOUNT_LINKEDIN.format("_get_linkedin_daily_statistics"),
            autospec=True,
            **(
                {"side_effect": side_effect}
                if side_effect
                else {"return_value": dict(buckets or {})}
            ),
        )

    def _statistics_of(self, account):
        return self.env["social.account.statistics"].search(
            [("account_id", "=", account.id)]
        )

    def _fake_urns(self, prefix, count):
        """Return URNs as long as the ones LinkedIn answers."""
        return [f"{prefix}{7132564752928563200 + index}" for index in range(count)]

    def _linkedin_query_string(self, call):
        """Rebuild the query string that a ``_request_linkedin`` call sends."""
        kwargs = call.kwargs
        return "&".join(
            social_url_encode(param_field, kwargs["params_values"])
            for param_field in kwargs["params_fields"]
        )

    @contextmanager
    def _patch_recent_statistics(self, statistics=None, side_effect=None):
        """Answer the finder of the daily buckets without calling LinkedIn.

        One patch and one only: the sweep of the pass reads the buckets and
        the check compares against those very buckets, so the whole pass now
        hangs on ``_get_linkedin_daily_statistics``. Patching it alone is what
        makes the number of calls per pass assertable.

        The figures are given in the watched form the assertions are written
        in and handed back as the six-figure buckets the finder answers.

        :param statistics: the watched figures every account answers with.
        :param side_effect: an exception to raise, or a callable taking the
            account and returning its watched figures.
        :return: the mock of ``_get_linkedin_daily_statistics``.
        """
        watched = RECENT_STATISTICS_LINKEDIN if statistics is None else statistics

        def daily_statistics(account, *_args, **_kwargs):
            if side_effect is None:
                return _linkedin_buckets(watched)
            if isinstance(side_effect, BaseException):
                raise side_effect
            return _linkedin_buckets(side_effect(account))

        with self._patch_reader(side_effect=daily_statistics) as mock_reader:
            yield mock_reader
