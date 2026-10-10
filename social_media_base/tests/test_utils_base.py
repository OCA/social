# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from unittest.mock import patch

import pytz
from dateutil.relativedelta import relativedelta

from odoo.exceptions import ValidationError

from odoo.addons.social_media_base.social_utils import (
    _generate_timestamps,
    convert_date_in_time,
    convert_to_date,
    convert_to_days,
    get_weeks,
    replace_repetitions,
    social_url_encode,
)
from odoo.addons.social_media_base.tests.test_social_common import (
    TestSocialMediaBaseCommon,
)

from .test_social_common import PATCH_SOCIAL_BASE_UTILS


class TestUtilsBase(TestSocialMediaBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixed_now = datetime(2025, 5, 30, 12, 0, 0, tzinfo=pytz.UTC)
        cls.date_start = "2025-01-01"
        cls.date_end = "2025-02-01"

    def test_convert_to_days(self):
        result = convert_to_days(seconds=50)
        self.assertEqual(result, 50 / 60 / 60 / 24)

        result = convert_to_days(miliseconds=10000)
        self.assertEqual(result, 10000 / 1000 / 60 / 60 / 24)

    def test_convert_to_date(self):
        result = convert_to_date(miliseconds=10000)
        self.assertEqual(result, datetime.now().date())

        result = convert_to_date(miliseconds=10000, time_zone="UTC")
        self.assertEqual(result, datetime.now().date())

        result = convert_to_date(
            miliseconds=10000, time_zone="UTC", date_add=datetime.now()
        )
        self.assertEqual(result.date(), datetime.now().date())

    @patch(PATCH_SOCIAL_BASE_UTILS.format("convert_to_date"))
    @patch(PATCH_SOCIAL_BASE_UTILS.format("datetime"))
    def test_convert_date_in_time(self, mock_datetime, mock_convert_to_date):
        seconds = timedelta(seconds=45)
        val_date = self.fixed_now - seconds
        mock_convert_to_date.return_value = val_date
        mock_datetime.now.return_value = self.fixed_now
        result = convert_date_in_time(miliseconds=50, timezone="UTC")
        self.assertEqual(result, "45 seconds")

        minutes = timedelta(minutes=45)
        val_date = self.fixed_now - minutes
        mock_convert_to_date.return_value = val_date
        mock_datetime.now.return_value = self.fixed_now
        result = convert_date_in_time(miliseconds=50, timezone="UTC")
        self.assertEqual(result, "45 minutes")

        hours = timedelta(hours=2)
        val_date = self.fixed_now - hours
        mock_convert_to_date.return_value = val_date
        mock_datetime.now.return_value = self.fixed_now
        result = convert_date_in_time(miliseconds=50, timezone="UTC")
        self.assertEqual(result, "2 hours")

        days = timedelta(days=2)
        val_date = self.fixed_now - days
        mock_convert_to_date.return_value = val_date
        mock_datetime.now.return_value = self.fixed_now
        result = convert_date_in_time(miliseconds=50, timezone="UTC")
        self.assertEqual(result, "2 days")

        months = relativedelta(months=2)
        val_date = self.fixed_now - months
        mock_convert_to_date.return_value = val_date
        mock_datetime.now.return_value = self.fixed_now
        result = convert_date_in_time(miliseconds=50, timezone="UTC")
        self.assertEqual(result, "2 months")

    def test_social_url_encode(self):
        params_values = {
            "q": "authors",
            "authors": ["urn:li:organization:123456789"],
        }
        result = social_url_encode("authors", params_values, {})
        self.assertEqual(result, "authors=List(urn%3Ali%3Aorganization%3A123456789)")

        params_values = {"author": "urn:li:organization:123456789"}
        result = social_url_encode("author", params_values, {})
        self.assertEqual(result, "author=urn%3Ali%3Aorganization%3A123456789")

        params_values = {"author": "urn:li:organization:123456789"}
        result = social_url_encode("author", params_values, {"author": [{"all": ":"}]})
        self.assertEqual(result, "author=urn:li:organization:123456789")

    def test_generate_timestamps(self):
        result = _generate_timestamps(
            date_start=self.date_start, date_end=self.date_end
        )
        self.assertEqual(result[0], 1735689600000)
        self.assertEqual(result[1], 3474057600000)

    def test_get_weeks(self):
        with self.assertRaises(ValidationError):
            get_weeks(start_date=self.date_start, end_date=self.date_end, freq="W-MONN")

        result = get_weeks(start_date=self.date_start, end_date=self.date_end, freq="D")
        self.assertEqual(len(result), 32)
        self.assertIsInstance(result, list)

        result = get_weeks(start_date=self.date_start, end_date=self.date_end)
        self.assertEqual(len(result), 4)
        self.assertIsInstance(result, list)

        result = get_weeks(
            start_date=self.date_start, end_date=self.date_end, freq="ME"
        )
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result, list)

    def test_replace_repetitions(self):
        text_test = "rep-la-ce-all"
        result = replace_repetitions(text_test, "-", "X", [3, 5, 7])
        self.assertEqual(result, "rep-la-ceXall")
