# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import os
import time
from datetime import date, datetime

import pytz

from odoo.addons.social_media_linkedin.social_linkedin_utils import (
    epoch_milliseconds,
    social_url_encode,
)
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    TestSocialCommonLinkedin,
)

# --- The contract of social_url_encode -----------------------------------
#
# Frozen from what the implementation produced over every call site of the
# repository, checked against the live API. Three rules are what these
# strings encode:
#
#   * a list becomes ``List(a,b,c)``: the parentheses of the wrapper and the
#     commas between the elements stay raw, because that is the Rest.li
#     syntax the APIs read;
#   * the colon goes both ways. Rest.li parses a parameter as a structure,
#     so a raw ":" is a field separator. A struct keeps its colons; a URN is
#     an opaque string and travels as "%3A", or the API answers
#     ILLEGAL_ARGUMENT. A value opening with "(" is a struct;
#   * everything else goes through ``quote``, so a space becomes "%20" and
#     the padding of a base64 cursor becomes "%3D".
#
# The line number of a label is the call the case was taken from.

_TOKEN = "AQXbLNzS8pWq3rF7kJ0mYt2vX9dHcE1aZbQwR4sT6uY8iO0pLkJhGfDsAzXcVbNm"
# Not a credential: only the base64 padding of the tail is under test.
_CLIENT_SECRET = "test_client_secret_aB3cD4=="
_ORG_URN = "urn:li:organization:96482531"
_PERSON_URN = "urn:li:person:8f2Xk3LmQ9"
_SHARE_URNS = [
    "urn:li:share:6912345678901234567",
    "urn:li:share:6912345678901234568",
]
_UGC_URNS = [
    "urn:li:ugcPost:7132564752928563200",
    "urn:li:ugcPost:7132564752928563201",
]
_IMAGE_URNS = [
    "urn:li:image:D4E10AQHxYzKq9pLmNw",
    "urn:li:image:D4E10AQFbTt3sVn2QkA",
]
_CAMPAIGN_URNS = [
    "urn:li:sponsoredCampaign:45",
    "urn:li:sponsoredCampaign:67",
]
_CREATIVE_URNS = [
    "urn:li:sponsoredCreative:888",
    "urn:li:sponsoredCreative:889",
]
_FIELDS_STATISTIC = (
    "actionClicks,adUnitClicks,clicks,costInUsd,"
    "externalWebsiteConversions,impressions,pivotValues"
)

ENCODED_QUERY_PARAMETERS = [
    # social_media_linkedin/models/social_account.py:284 _refresh_token()
    (
        "linkedin:284 grant_type",
        "grant_type",
        "refresh_token",
        "grant_type=refresh_token",
    ),
    (
        "linkedin:284 refresh_token",
        "refresh_token",
        _TOKEN,
        "refresh_token=AQXbLNzS8pWq3rF7kJ0mYt2vX9dHcE1aZbQwR4sT6uY8iO0pLkJhGfDsAzXcVbN"
        "m",
    ),
    (
        "linkedin:284 client_id",
        "client_id",
        "86xk9v0abcd12e",
        "client_id=86xk9v0abcd12e",
    ),
    # The one non-list value that carries base64 padding.
    (
        "linkedin:284 client_secret",
        "client_secret",
        _CLIENT_SECRET,
        "client_secret=test_client_secret_aB3cD4%3D%3D",
    ),
    # :354 / :483 the image and the video upload.
    (
        "linkedin:354 action",
        "action",
        "initializeUpload",
        "action=initializeUpload",
    ),
    (
        "linkedin:483 action",
        "action",
        "finalizeUpload",
        "action=finalizeUpload",
    ),
    # :1085 _get_posts(), the finder and the batch get.
    (
        "linkedin:1085 q",
        "q",
        "author",
        "q=author",
    ),
    (
        "linkedin:1085 author",
        "author",
        _ORG_URN,
        "author=urn%3Ali%3Aorganization%3A96482531",
    ),
    (
        "linkedin:1085 count",
        "count",
        100,
        "count=100",
    ),
    (
        "linkedin:1085 start",
        "start",
        200,
        "start=200",
    ),
    (
        "linkedin:1085 sortBy",
        "sortBy",
        "LAST_MODIFIED",
        "sortBy=LAST_MODIFIED",
    ),
    (
        "linkedin:1085 ids one share",
        "ids",
        [_SHARE_URNS[0]],
        "ids=List(urn%3Ali%3Ashare%3A6912345678901234567)",
    ),
    (
        "linkedin:1085 ids one ugcPost",
        "ids",
        [_UGC_URNS[0]],
        "ids=List(urn%3Ali%3AugcPost%3A7132564752928563200)",
    ),
    # :1168 the only list holding several separate elements.
    (
        "linkedin:1168 ids images",
        "ids",
        _IMAGE_URNS,
        "ids=List(urn%3Ali%3Aimage%3AD4E10AQHxYzKq9pLmNw,urn%3Ali%3Aimage%3AD4E10AQFbT"
        "t3sVn2QkA)",
    ),
    # :1290 _get_entity_share_statistics().
    (
        "linkedin:1290 organizationalEntity",
        "organizationalEntity",
        _ORG_URN,
        "organizationalEntity=urn%3Ali%3Aorganization%3A96482531",
    ),
    (
        "linkedin:1290 shares",
        "shares",
        [",".join(_SHARE_URNS)],
        "shares=List(urn%3Ali%3Ashare%3A6912345678901234567,urn%3Ali%3Ashare%3A6912345"
        "678901234568)",
    ),
    (
        "linkedin:1290 ugcPosts",
        "ugcPosts",
        [",".join(_UGC_URNS)],
        "ugcPosts=List(urn%3Ali%3AugcPost%3A7132564752928563200,urn%3Ali%3AugcPost%3A7"
        "132564752928563201)",
    ),
    # :1441 _get_ugc_posts_statistics(), the /socialActions batch get.
    (
        "linkedin:1441 ids ugcPosts",
        "ids",
        [",".join(_UGC_URNS)],
        "ids=List(urn%3Ali%3AugcPost%3A7132564752928563200,urn%3Ali%3AugcPost%3A713256"
        "4752928563201)",
    ),
    # :1859 _get_linkedin_daily_statistics(). The Rest.li struct that used
    # to need an exception of its own so that its colons survived.
    (
        "linkedin:1859 timeIntervals",
        "timeIntervals",
        "(timeRange:(start:1748563200000,end:1751155200000)"
        ",timeGranularityType:DAY)",
        "timeIntervals=(timeRange:(start:1748563200000,end:1751155200000),timeGranular"
        "ityType:DAY)",
    ),
    # The actor of a publication, on the comments preview.
    (
        "linkedin actor",
        "actor",
        _PERSON_URN,
        "actor=urn%3Ali%3Aperson%3A8f2Xk3LmQ9",
    ),
    # social_media_advertising_linkedin/models/social_account.py:132
    (
        "advertising:132 q",
        "q",
        "authenticatedUser",
        "q=authenticatedUser",
    ),
    (
        "advertising:132 start",
        "start",
        0,
        "start=0",
    ),
    # :250 _fetch_linkedin_creatives().
    (
        "advertising:250 sortOrder",
        "sortOrder",
        "ASCENDING",
        "sortOrder=ASCENDING",
    ),
    (
        "advertising:250 pageSize",
        "pageSize",
        100,
        "pageSize=100",
    ),
    (
        "advertising:250 campaigns",
        "campaigns",
        _CAMPAIGN_URNS,
        "campaigns=List(urn%3Ali%3AsponsoredCampaign%3A45,urn%3Ali%3AsponsoredCampaign"
        "%3A67)",
    ),
    # A paging cursor: base64, so its padding is escaped.
    (
        "advertising:250 pageToken",
        "pageToken",
        "aBc123XyZ456==",
        "pageToken=aBc123XyZ456%3D%3D",
    ),
    # :306 _fetch_linkedin_ad_entities(), the search finder.
    (
        "advertising:306 search test",
        "search",
        "(test:false)",
        "search=(test:false)",
    ),
    (
        "advertising:306 search status",
        "search",
        "(status:(values:List(ACTIVE)))",
        "search=(status:(values:List(ACTIVE)))",
    ),
    (
        "advertising:306 fields",
        "fields",
        "id,name,status",
        "fields=id,name,status",
    ),
    # :759 _fetch_linkedin_ad_statistics(), the analytics finder.
    (
        "advertising:759 pivots",
        "pivots",
        ["CAMPAIGN"],
        "pivots=List(CAMPAIGN)",
    ),
    (
        "advertising:759 timeGranularity",
        "timeGranularity",
        "ALL",
        "timeGranularity=ALL",
    ),
    (
        "advertising:759 dateRange",
        "dateRange",
        "(start:(year:2025,month:1,day:1),end:(year:2025,month:2,day:1))",
        "dateRange=(start:(year:2025,month:1,day:1),end:(year:2025,month:2,day:1))",
    ),
    (
        "advertising:759 fields",
        "fields",
        _FIELDS_STATISTIC,
        "fields=actionClicks,adUnitClicks,clicks,costInUsd,externalWebsiteConversions,"
        "impressions,pivotValues",
    ),
    (
        "advertising:759 creatives",
        "creatives",
        _CREATIVE_URNS,
        "creatives=List(urn%3Ali%3AsponsoredCreative%3A888,urn%3Ali%3AsponsoredCreativ"
        "e%3A889)",
    ),
    # A list of plain integers still becomes a Rest.li list.
    (
        "a list of integers",
        "ids",
        [1, 2],
        "ids=List(1,2)",
    ),
]


class TestSocialUrlEncode(TestSocialCommonLinkedin):
    def test_every_call_site_of_the_repository(self):
        """Each real parameter encodes to the string frozen for it."""
        for label, param_field, value, expected in ENCODED_QUERY_PARAMETERS:
            with self.subTest(case=label):
                self.assertEqual(
                    social_url_encode(param_field, {param_field: value}), expected
                )

    def test_the_colon_of_a_urn_is_escaped(self):
        """A URN is opaque, so its colons must not read as separators.

        LinkedIn answers ILLEGAL_ARGUMENT to a raw one: Rest.li parses the
        value as a structure instead of as the string it is.
        """
        self.assertEqual(
            social_url_encode("author", {"author": "urn:li:organization:123"}),
            "author=urn%3Ali%3Aorganization%3A123",
        )
        self.assertEqual(
            social_url_encode(
                "authors",
                {"authors": ["urn:li:organization:123", "urn:li:person:abc"]},
            ),
            "authors=List(urn%3Ali%3Aorganization%3A123,urn%3Ali%3Aperson%3Aabc)",
        )

    def test_a_restli_struct_keeps_its_separators(self):
        """The colons of a struct are what its fields are read by."""
        self.assertEqual(
            social_url_encode(
                "timeIntervals",
                {
                    "timeIntervals": "(timeRange:(start:1,end:2)"
                    ",timeGranularityType:DAY)"
                },
            ),
            "timeIntervals=(timeRange:(start:1,end:2),timeGranularityType:DAY)",
        )

    def test_what_is_still_escaped(self):
        """Everything outside the safe set goes through ``quote``."""
        self.assertEqual(
            social_url_encode("search", {"search": "50% off"}),
            "search=50%25%20off",
        )
        self.assertEqual(
            social_url_encode("q", {"q": "a+b"}),
            "q=a%2Bb",
        )
        # The safe set replaces the "/" that ``quote`` keeps by default, so a
        # slash is escaped too. The encoder builds one parameter, never a URL.
        self.assertEqual(
            social_url_encode("url", {"url": "https://a/b?c=d&e=f"}),
            "url=https%3A%2F%2Fa%2Fb%3Fc%3Dd%26e%3Df",
        )

    def test_a_comma_separates_instead_of_being_escaped(self):
        """``fields`` names several fields with commas the API reads."""
        self.assertEqual(
            social_url_encode("fields", {"fields": "id,name,status"}),
            "fields=id,name,status",
        )


class TestEpochMilliseconds(TestSocialCommonLinkedin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixed_now = datetime(2025, 5, 30, 12, 0, 0, tzinfo=pytz.UTC)
        cls.date_start = "2025-01-01"
        cls.date_end = "2025-02-01"

    def test_epoch_milliseconds(self):
        self.assertEqual(epoch_milliseconds(self.date_start), 1735689600000)
        self.assertEqual(epoch_milliseconds(self.date_end), 1738368000000)

    def test_epoch_milliseconds_accepts_what_the_orm_reads(self):
        """A string, a date and a datetime all name the same moment."""
        expected = 1735689600000
        self.assertEqual(epoch_milliseconds("2025-01-01"), expected)
        self.assertEqual(epoch_milliseconds(date(2025, 1, 1)), expected)
        self.assertEqual(epoch_milliseconds(datetime(2025, 1, 1)), expected)

    def _run_under_timezone(self, timezone_name):
        """Run the rest of the test with the process under ``timezone_name``.

        ``datetime.timestamp()`` reads a naive value as local time, so the
        only way to prove the conversion does not depend on the host is to
        move the host.
        """
        previous = os.environ.get("TZ")
        self.addCleanup(time.tzset)
        if previous is None:
            self.addCleanup(os.environ.pop, "TZ", None)
        else:
            self.addCleanup(os.environ.__setitem__, "TZ", previous)
        os.environ["TZ"] = timezone_name
        time.tzset()

    def test_epoch_milliseconds_ignores_the_process_timezone(self):
        """A naive value is UTC, whatever ``TZ`` the process runs under."""
        for timezone_name in ("UTC", "Europe/Madrid", "America/New_York"):
            with self.subTest(timezone=timezone_name):
                self._run_under_timezone(timezone_name)
                self.assertEqual(epoch_milliseconds(self.date_start), 1735689600000)
                self.assertEqual(epoch_milliseconds(self.date_end), 1738368000000)

    def test_epoch_milliseconds_rejects_an_aware_datetime(self):
        """An aware datetime is a mistake, and it is pointed at, not tolerated."""
        with self.assertRaises(ValueError):
            epoch_milliseconds(self.fixed_now)
