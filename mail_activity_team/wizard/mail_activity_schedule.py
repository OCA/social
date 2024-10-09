# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class MailActivitySchedule(models.TransientModel):
    _inherit = "mail.activity.schedule"

    def _get_default_team_id(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        res_model = self.env.context.get("default_res_model")
        model = self.sudo().env["ir.model"].search([("model", "=", res_model)], limit=1)
        domain = [("member_ids", "in", [user_id])]
        if res_model:
            domain.extend(
                ["|", ("res_model_ids", "=", False), ("res_model_ids", "in", model.ids)]
            )
        return self.env["mail.activity.team"].search(domain, limit=1)

    team_user_id = fields.Many2one(
        string="Team user", related="activity_user_id", readonly=False
    )

    team_id = fields.Many2one(
        comodel_name="mail.activity.team", default=lambda s: s._get_default_team_id()
    )
