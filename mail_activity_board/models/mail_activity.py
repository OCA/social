# Copyright 2018 David Juaneda - <djuaneda@sdi.es>
# Copyright 2018 ForgeFlow S.L.  <https://www.forgeflow.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    res_model_id_name = fields.Char(
        related="res_model_id.name", string="Origin", readonly=True
    )
    duration = fields.Float(related="calendar_event_id.duration", readonly=True)
    calendar_event_id_start = fields.Datetime(
        related="calendar_event_id.start", readonly=True
    )
    calendar_event_id_partner_ids = fields.Many2many(
        related="calendar_event_id.partner_ids", readonly=True
    )

    def open_origin(self):
        self.ensure_one()
        vid = self.env[self.res_model].browse(self.res_id).get_formview_id()
        response = {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "view_mode": "form",
            "res_id": self.res_id,
            "target": "current",
            "flags": {"form": {"action_buttons": False}},
            "views": [(vid, "form")],
        }
        return response

    @api.model
    def action_activities_board(self):
        action = self.env.ref("mail_activity_board.open_boards_activities").read()[0]
        return action

    @api.model
    def _find_allowed_model_wise(self, doc_model, doc_dict):
        doc_ids = list(doc_dict)
        allowed_doc_ids = (
            self.env[doc_model]
            .with_context(active_test=False)
            .search([("id", "in", doc_ids)])
            .ids
        )
        return {
            message_id
            for allowed_doc_id in allowed_doc_ids
            for message_id in doc_dict[allowed_doc_id]
        }

    @api.model
    def _find_allowed_doc_ids(self, model_ids):
        ir_model_access_model = self.env["ir.model.access"]
        allowed_ids = set()
        for doc_model, doc_dict in model_ids.items():
            if not ir_model_access_model.check(doc_model, "read", False):
                continue
            allowed_ids |= self._find_allowed_model_wise(doc_model, doc_dict)
        return allowed_ids
