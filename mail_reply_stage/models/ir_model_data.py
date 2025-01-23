# Copyright 2025 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class IrModelData(models.Model):
    _inherit = "ir.model.data"

    @api.model
    def _name_search(
        self, name, args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        stage_model = self.env.context.get("mail_reply_stage_model")
        if name and stage_model:
            stage_ids = self.env[stage_model]._search(
                [("name", operator, name)], limit=limit, access_rights_uid=name_get_uid
            )
            domain = [("model", "=", stage_model), ("res_id", "in", stage_ids)]
            xml_ids = self._search(domain, limit=limit, access_rights_uid=name_get_uid)
            return xml_ids
        return super()._name_search(
            name=name,
            args=args,
            operator=operator,
            limit=limit,
            name_get_uid=name_get_uid,
        )
