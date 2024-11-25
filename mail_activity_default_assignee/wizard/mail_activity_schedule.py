# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailActivitySchedule(models.TransientModel):
    _inherit = "mail.activity.schedule"

    @api.depends("activity_type_id", "res_ids")
    def _compute_activity_user_id(self):
        res = super()._compute_activity_user_id()
        for scheduler in self.filtered(
            lambda rec: not rec.activity_type_id.default_user_id
            and rec.activity_type_id.default_user_field_id
        ):
            fname = scheduler.activity_type_id.default_user_field_id.name
            if users := scheduler._get_applied_on_records().mapped(fname):
                scheduler.activity_user_id = users[:1]
        return res
