# Copyright 2026 Binhex Cloud
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2.errors import CheckViolation

from odoo.exceptions import AccessError
from odoo.tests import new_test_user
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseCommon


class TestUtmCampaign(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.campaign_model = cls.env["utm.campaign"]
        cls.campaign = cls.campaign_model.create(
            {
                "name": "Budgeted campaign",
                "campaign_budget_amount": 1000,
                "actual_cost": 400,
            }
        )
        cls.salesperson = new_test_user(
            cls.env,
            login="test-salesperson",
            groups="sales_team.group_sale_salesman",
            password="Password1234!",
        )
        cls.no_access_user = new_test_user(
            cls.env,
            login="test-no-access",
            groups="base.group_user",
            password="Password1234!",
        )

    def test_budget_amount_negative_constraint(self):
        with (
            mute_logger("odoo.sql_db"),
            self.assertRaises(CheckViolation),
            self.env.cr.savepoint(),
        ):
            self.campaign_model.create(
                {"name": "Invalid budget", "campaign_budget_amount": -1}
            )

    def test_actual_cost_negative_constraint(self):
        with (
            mute_logger("odoo.sql_db"),
            self.assertRaises(CheckViolation),
            self.env.cr.savepoint(),
        ):
            self.campaign_model.create({"name": "Invalid cost", "actual_cost": -1})

    def test_budget_amount_negative_constraint_on_write(self):
        with (
            mute_logger("odoo.sql_db"),
            self.assertRaises(CheckViolation),
            self.env.cr.savepoint(),
        ):
            self.campaign.write({"campaign_budget_amount": -1})

    def test_actual_cost_negative_constraint_on_write(self):
        with (
            mute_logger("odoo.sql_db"),
            self.assertRaises(CheckViolation),
            self.env.cr.savepoint(),
        ):
            self.campaign.write({"actual_cost": -1})

    def test_zero_values_allowed(self):
        campaign = self.campaign_model.create(
            {"name": "Zero budget", "campaign_budget_amount": 0, "actual_cost": 0}
        )
        self.assertEqual(campaign.campaign_budget_amount, 0)
        self.assertEqual(campaign.actual_cost, 0)

    def test_unset_values_allowed(self):
        campaign = self.campaign_model.create({"name": "No budget set"})
        self.assertFalse(campaign.campaign_budget_amount)
        self.assertFalse(campaign.actual_cost)

    def test_currency_defaults_to_company_currency(self):
        self.assertEqual(
            self.campaign.currency_id, self.campaign.company_id.currency_id
        )

    def test_currency_is_related_to_company_currency(self):
        field = self.campaign_model._fields["currency_id"]
        self.assertEqual(field.related, "company_id.currency_id")

    def test_budget_fields_visible_to_salesperson(self):
        campaign = self.campaign.with_user(self.salesperson)
        campaign.write({"campaign_budget_amount": 2000})
        self.assertEqual(campaign.campaign_budget_amount, 2000)

    def test_budget_fields_write_restricted_without_sales_group(self):
        campaign = self.campaign.with_user(self.no_access_user)
        with self.assertRaises(AccessError):
            campaign.write({"campaign_budget_amount": 2000})

    def test_budget_fields_read_restricted_without_sales_group(self):
        campaign = self.campaign.with_user(self.no_access_user)
        with self.assertRaises(AccessError):
            campaign.read(["campaign_budget_amount"])
