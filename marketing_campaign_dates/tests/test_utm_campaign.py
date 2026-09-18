# Copyright 2026 Binhex Cloud
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree
from psycopg2.errors import CheckViolation

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger
from odoo.tools.safe_eval import safe_eval


class TestUtmCampaign(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.campaign_model = cls.env["utm.campaign"]
        cls.search_view = cls.env.ref(
            "marketing_campaign_dates.utm_campaign_view_search_inherit"
        )
        today = fields.Date.today()

        cls.campaign_no_dates = cls.campaign_model.create(
            {"name": "No dates"},
        )
        cls.campaign_running = cls.campaign_model.create(
            {
                "name": "Running",
                "start_date": fields.Date.subtract(today, days=1),
                "end_date": fields.Date.add(today, days=14),
            }
        )
        cls.campaign_upcoming = cls.campaign_model.create(
            {
                "name": "Upcoming",
                "start_date": fields.Date.add(today, days=7),
                "end_date": fields.Date.add(today, days=30),
            }
        )
        cls.campaign_finished = cls.campaign_model.create(
            {
                "name": "Finished",
                "start_date": fields.Date.subtract(today, days=20),
                "end_date": fields.Date.subtract(today, days=1),
            }
        )
        cls.campaign_start_only = cls.campaign_model.create(
            {
                "name": "Start date only",
                "start_date": fields.Date.subtract(today, days=1),
            }
        )
        cls.campaign_end_only = cls.campaign_model.create(
            {
                "name": "End date only",
                "end_date": fields.Date.add(today, days=1),
            }
        )
        cls.campaign_starts_today = cls.campaign_model.create(
            {
                "name": "Starts today",
                "start_date": today,
                "end_date": fields.Date.add(today, days=1),
            }
        )
        cls.campaign_ends_today = cls.campaign_model.create(
            {
                "name": "Ends today",
                "start_date": fields.Date.subtract(today, days=1),
                "end_date": today,
            }
        )

    def _get_filter_domain(self, filter_name):
        """Read the domain straight from the search view arch, so the test
        exercises the actual filter instead of a hand copied duplicate."""
        arch = etree.fromstring(self.search_view.arch)
        (filter_node,) = arch.xpath(f"//filter[@name='{filter_name}']")
        context_today = lambda: fields.Date.context_today(  # noqa: E731
            self.campaign_model
        )
        return safe_eval(filter_node.get("domain"), {"context_today": context_today})

    def test_end_date_before_start_date_constraint(self):
        today = fields.Date.today()
        with (
            mute_logger("odoo.sql_db"),
            self.assertRaises(CheckViolation),
            self.env.cr.savepoint(),
        ):
            self.campaign_model.create(
                {
                    "name": "Invalid dates",
                    "start_date": today,
                    "end_date": fields.Date.subtract(today, days=1),
                }
            )

    def test_end_date_before_start_date_constraint_on_write(self):
        today = fields.Date.today()
        with (
            mute_logger("odoo.sql_db"),
            self.assertRaises(CheckViolation),
            self.env.cr.savepoint(),
        ):
            self.campaign_running.write(
                {"start_date": today, "end_date": fields.Date.subtract(today, days=1)}
            )

    def test_equal_start_and_end_date_allowed(self):
        today = fields.Date.today()
        campaign = self.campaign_model.create(
            {"name": "Single day", "start_date": today, "end_date": today}
        )
        self.assertEqual(campaign.start_date, campaign.end_date)

    def test_running_filter(self):
        campaigns = self.campaign_model.search(self._get_filter_domain("running"))
        self.assertIn(self.campaign_running, campaigns)
        self.assertIn(self.campaign_no_dates, campaigns)
        self.assertIn(self.campaign_start_only, campaigns)
        self.assertIn(self.campaign_end_only, campaigns)
        self.assertIn(self.campaign_starts_today, campaigns)
        self.assertIn(self.campaign_ends_today, campaigns)
        self.assertNotIn(self.campaign_upcoming, campaigns)
        self.assertNotIn(self.campaign_finished, campaigns)

    def test_upcoming_filter(self):
        campaigns = self.campaign_model.search(self._get_filter_domain("upcoming"))
        self.assertIn(self.campaign_upcoming, campaigns)
        self.assertNotIn(self.campaign_running, campaigns)
        self.assertNotIn(self.campaign_finished, campaigns)
        self.assertNotIn(self.campaign_no_dates, campaigns)
        self.assertNotIn(self.campaign_starts_today, campaigns)

    def test_finished_filter(self):
        campaigns = self.campaign_model.search(self._get_filter_domain("finished"))
        self.assertIn(self.campaign_finished, campaigns)
        self.assertNotIn(self.campaign_running, campaigns)
        self.assertNotIn(self.campaign_upcoming, campaigns)
        self.assertNotIn(self.campaign_no_dates, campaigns)
        self.assertNotIn(self.campaign_ends_today, campaigns)
