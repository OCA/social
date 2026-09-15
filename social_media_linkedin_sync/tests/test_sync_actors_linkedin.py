# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from odoo import _
from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
)

from .test_sync_linkedin_common import TestSocialSyncCommonLinkedin

ORGANIZATION_URN = "urn:li:organization:789"
OTHER_ORGANIZATION_URN = "urn:li:organization:790"
PERSON_URN = "urn:li:person:AbC123"
LOGGER_ACCOUNT_SYNC_LINKEDIN = (
    "odoo.addons.social_media_linkedin_sync.models.social_account"
)
LOGO_URL = "https://media.licdn.com/dms/image/logo_400_400.png"


def _organization_payload(name, logo_url=LOGO_URL):
    """The organization as the Organizations API answers it."""
    payload = {"id": 789, "name": {"localized": {"en_US": name}}}
    if logo_url:
        payload["logoV2"] = {
            "original~": {
                "elements": [
                    {
                        "artifact": "urn:li:digitalmediaMediaArtifact:(x,logo_400_400)",
                        "identifiers": [{"identifier": logo_url}],
                    }
                ]
            }
        }
    return payload


class TestSocialSyncActorsLinkedin(TestSocialSyncCommonLinkedin):
    """Who a comment of LinkedIn is drawn as.

    LinkedIn identifies the author of a comment by a URN and nothing else, so
    what the client draws is decided here: the account itself, an
    organization that can be read, and a neutral label for everything else.
    Attributing a comment to whoever published is what these tests exist to
    stop.
    """

    def _linkedin_side_effect(self, comments, organizations=None):
        """Answer each endpoint of a thread the way LinkedIn does.

        One mock stands for every call because they all travel through
        ``_request_linkedin``: the comments and the reactions answer a
        ``requests.Response``, the organizations answer the parsed body.

        :param comments: the elements of the thread.
        :param organizations: ``{urn: payload or status code}``; a code
            answers a refusal, and an organization not named here is refused
            with a ``403``.
        """
        organizations = organizations or {}

        def side_effect(*args, **kwargs):
            endpoint = kwargs.get("endpoint") or ""
            if endpoint.startswith("/organizations/"):
                organization_id = endpoint.rsplit("/", 1)[-1]
                answer = organizations.get(
                    f"urn:li:organization:{organization_id}", 403
                )
                if isinstance(answer, dict):
                    return answer
                response = MagicMock()
                response.status_code = answer
                return response
            response = MagicMock()
            response.status_code = 200
            if endpoint == "/reactions":
                response.json.return_value = {"results": {}}
            else:
                response.json.return_value = {
                    "paging": {"total": len(comments)},
                    "elements": comments,
                }
            return response

        return side_effect

    def _comment(self, actor, comment_id="1"):
        """One comment of a thread, signed by ``actor``."""
        return {
            "$URN": f"urn:li:comment:(urn:li:activity:6666,{comment_id})",
            "id": comment_id,
            "object": "urn:li:activity:6666",
            "lastModified": {"actor": actor, "time": 1757320000000},
            "message": {"text": "Great post!"},
            "content": [],
        }

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_linkedin_actors_reads_the_organization(self, mock_request):
        """An organization is the one actor LinkedIn lets us name."""
        mock_request.side_effect = self._linkedin_side_effect(
            [], {ORGANIZATION_URN: _organization_payload("Acme Corporation")}
        )
        actors = self.SocialAccountLinkedin._get_linkedin_actors([ORGANIZATION_URN])
        self.assertEqual(
            actors,
            {ORGANIZATION_URN: {"name": "Acme Corporation", "image": LOGO_URL}},
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_linkedin_actors_asks_nothing_about_the_account(self, mock_request):
        """The account and a person are dropped before any call is made."""
        mock_request.side_effect = self._linkedin_side_effect([])
        actors = self.SocialAccountLinkedin._get_linkedin_actors(
            [self.SocialAccountLinkedin.remote_ref, PERSON_URN, False, {}]
        )
        self.assertEqual(actors, {})
        self.assertFalse(
            mock_request.called,
            msg="Neither the account nor a person has anything to ask "
            "LinkedIn about.",
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_linkedin_actors_survives_a_refusal(self, mock_request):
        """A ``403`` on one organization leaves the rest of the batch alone."""
        mock_request.side_effect = self._linkedin_side_effect(
            [],
            {
                ORGANIZATION_URN: 403,
                OTHER_ORGANIZATION_URN: _organization_payload("Acme Corporation"),
            },
        )
        actors = self.SocialAccountLinkedin._get_linkedin_actors(
            [ORGANIZATION_URN, OTHER_ORGANIZATION_URN]
        )
        self.assertEqual(
            list(actors),
            [OTHER_ORGANIZATION_URN],
            msg="The organization LinkedIn refuses is left out, and the "
            "caller draws it with a neutral label.",
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_draws_the_account_itself(self, mock_request):
        """A comment written by the account is signed with its name."""
        account = self.SocialAccountLinkedin
        mock_request.side_effect = self._linkedin_side_effect(
            [self._comment(account.remote_ref)]
        )
        comment = self.SocialPostAccountLinkedin.get_comments()["data"][0]
        self.assertEqual(comment["actor"], account.name)
        self.assertEqual(
            comment["author_image"],
            f"/web/image/social.account/{account.id}/image_128",
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_labels_a_person(self, mock_request):
        """LinkedIn does not let a member be named, so none is invented."""
        mock_request.side_effect = self._linkedin_side_effect(
            [self._comment(PERSON_URN)]
        )
        comment = self.SocialPostAccountLinkedin.get_comments()["data"][0]
        self.assertEqual(comment["actor"], "LinkedIn member")
        self.assertFalse(
            comment["author_image"],
            msg="Without a picture the client draws a generic silhouette, "
            "never the avatar of the account.",
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_resolves_the_organization(self, mock_request):
        """An organization that answers is drawn with its name and its logo."""
        mock_request.side_effect = self._linkedin_side_effect(
            [self._comment(ORGANIZATION_URN)],
            {ORGANIZATION_URN: _organization_payload("Acme Corporation")},
        )
        comment = self.SocialPostAccountLinkedin.get_comments()["data"][0]
        self.assertEqual(comment["actor"], "Acme Corporation")
        self.assertEqual(comment["author_image"], LOGO_URL)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_labels_the_page_it_cannot_read(self, mock_request):
        """A page LinkedIn refuses does not cost the thread."""
        mock_request.side_effect = self._linkedin_side_effect(
            [self._comment(ORGANIZATION_URN)], {ORGANIZATION_URN: 403}
        )
        result = self.SocialPostAccountLinkedin.get_comments()
        self.assertTrue(result["success"])
        self.assertEqual(result["data"][0]["actor"], "LinkedIn page")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comments_asks_once_per_organization(self, mock_request):
        """One call per distinct organization, not one per comment."""
        mock_request.side_effect = self._linkedin_side_effect(
            [
                self._comment(ORGANIZATION_URN, "1"),
                self._comment(ORGANIZATION_URN, "2"),
                self._comment(OTHER_ORGANIZATION_URN, "3"),
                self._comment(self.SocialAccountLinkedin.remote_ref, "4"),
                self._comment(PERSON_URN, "5"),
            ],
            {
                ORGANIZATION_URN: _organization_payload("Acme Corporation"),
                OTHER_ORGANIZATION_URN: _organization_payload("Acme Supplies"),
            },
        )
        self.SocialPostAccountLinkedin.get_comments()
        organization_calls = [
            call
            for call in mock_request.call_args_list
            if (call.kwargs.get("endpoint") or "").startswith("/organizations/")
        ]
        self.assertEqual(len(organization_calls), 2)

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_comment_replies_resolves_the_actors(self, mock_request):
        """A reply is signed the same way a first-level comment is."""
        mock_request.side_effect = self._linkedin_side_effect(
            [self._comment(PERSON_URN)]
        )
        result = self.SocialPostAccountLinkedin.get_comment_replies(
            "urn:li:comment:(urn:li:activity:6666,999)"
        )
        self.assertEqual(result["data"][0]["actor"], "LinkedIn member")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_created_comment_is_signed_by_the_account(self, mock_request):
        """The comment just published is drawn without rereading the thread."""
        account = self.SocialAccountLinkedin
        mock_request.side_effect = self._linkedin_side_effect([])
        response = MagicMock()
        response.json.return_value = {
            "$URN": "urn:li:comment:(urn:li:activity:6666,999)",
            "id": "999",
            "object": "urn:li:activity:6666",
            "created": {"actor": account.remote_ref, "time": 1757320000000},
            "message": {"text": "Ok"},
            "content": [],
        }
        comment = self.SocialPostAccountLinkedin._linkedin_created_comment(response)
        self.assertEqual(comment["comment"]["actor"], account.name)
        self.assertEqual(
            comment["comment"]["author_image"],
            f"/web/image/social.account/{account.id}/image_128",
        )

    @mute_logger(LOGGER_ACCOUNT_SYNC_LINKEDIN)
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_linkedin_actors_survives_an_unreachable_linkedin(self, mock_request):
        """A name is never worth a thread, nor an import."""
        mock_request.side_effect = UserError(_("LinkedIn refused the organization"))
        self.assertEqual(
            self.SocialAccountLinkedin._get_linkedin_actors([ORGANIZATION_URN]), {}
        )

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_linkedin_actors_takes_any_language(self, mock_request):
        """Any name of the organization beats drawing the comment without one."""
        payload = _organization_payload("Acme Corporation")
        payload["name"] = {"localized": {"es_ES": "Acme Sociedad Anónima"}}
        mock_request.side_effect = self._linkedin_side_effect(
            [], {ORGANIZATION_URN: payload}
        )
        actors = self.SocialAccountLinkedin._get_linkedin_actors([ORGANIZATION_URN])
        self.assertEqual(actors[ORGANIZATION_URN]["name"], "Acme Sociedad Anónima")

    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_get_linkedin_actors_drops_the_organization_without_a_name(
        self, mock_request
    ):
        """An organization that answers no name is left to the neutral label."""
        payload = _organization_payload("Acme Corporation")
        payload["name"] = {"localized": {}}
        mock_request.side_effect = self._linkedin_side_effect(
            [self._comment(ORGANIZATION_URN)], {ORGANIZATION_URN: payload}
        )
        self.assertEqual(
            self.SocialAccountLinkedin._get_linkedin_actors([ORGANIZATION_URN]), {}
        )
        comment = self.SocialPostAccountLinkedin.get_comments()["data"][0]
        self.assertEqual(comment["actor"], "LinkedIn page")

    def test_actor_image_without_a_logo(self):
        """An organization LinkedIn reports no logo for is drawn without one."""
        account = self.SocialAccountLinkedin
        self.assertFalse(account._get_linkedin_actor_image({}))
        self.assertFalse(
            account._get_linkedin_actor_image(
                _organization_payload("Acme Corporation", logo_url=None)
            )
        )
        self.assertFalse(
            account._get_linkedin_actor_image(
                {"logoV2": {"original~": {"elements": [{"artifact": "x"}]}}}
            ),
            msg="An element carrying no identifier names no URL.",
        )

    def test_actor_image_falls_back_to_the_first_element(self):
        """Without the preferred size, the first stream LinkedIn lists answers."""
        organization = {
            "logoV2": {
                "original~": {
                    "elements": [
                        {
                            "artifact": "urn:li:digitalmediaMediaArtifact:(x,logo_200)",
                            "identifiers": [{"identifier": "https://first.png"}],
                        },
                        {
                            "artifact": "urn:li:digitalmediaMediaArtifact:(x,logo_100)",
                            "identifiers": [{"identifier": "https://second.png"}],
                        },
                    ]
                }
            }
        }
        self.assertEqual(
            self.SocialAccountLinkedin._get_linkedin_actor_image(organization),
            "https://first.png",
        )

    def test_actor_image_prefers_the_largest_logo(self):
        """The 400x400 stream is the one the dialog draws."""
        organization = {
            "logoV2": {
                "original~": {
                    "elements": [
                        {
                            "artifact": "urn:li:digitalmediaMediaArtifact:(x,logo_100)",
                            "identifiers": [{"identifier": "https://small.png"}],
                        },
                        {
                            "artifact": (
                                "urn:li:digitalmediaMediaArtifact:(x,logo_400_400)"
                            ),
                            "identifiers": [{"identifier": LOGO_URL}],
                        },
                    ]
                }
            }
        }
        self.assertEqual(
            self.SocialAccountLinkedin._get_linkedin_actor_image(organization),
            LOGO_URL,
        )
