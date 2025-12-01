# Copyright 2025 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.fields import Domain


class IrModelData(models.Model):
    _inherit = "ir.model.data"

    @api.model
    @api.readonly
    def name_search(
        self,
        name: str = "",
        domain=None,
        operator: str = "ilike",
        limit: int = 100,
    ):
        stage_model = self.env.context.get("mail_reply_stage_model")
        if name and stage_model:
            stage_ids = self.env[stage_model]._search(
                [("name", operator, name)], limit=limit
            )
            domain = [
                ("model", "=", stage_model),
                ("res_id", "in", stage_ids),
            ]
            records = self.search_fetch(Domain(domain), ["display_name"], limit=limit)
            return [(rec.id, rec.display_name) for rec in records]
        return super().name_search(
            name=name, domain=domain, operator=operator, limit=limit
        )
