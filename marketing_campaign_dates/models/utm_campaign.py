# Copyright 2026 Binhex Cloud
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class UtmCampaign(models.Model):
    _inherit = "utm.campaign"

    _sql_constraints = [
        (
            "end_date_after_start_date",
            "CHECK(end_date IS NULL OR start_date IS NULL "
            "OR end_date >= start_date)",
            "The end date cannot be earlier than the start date.",
        ),
    ]

    start_date = fields.Date(help="Date when the campaign starts.")
    end_date = fields.Date(help="Date when the campaign ends.")
