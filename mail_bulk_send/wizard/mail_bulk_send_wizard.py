# Copyright 2026 Quartile Limited
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailBulkSendWizard(models.TransientModel):
    _name = "mail.bulk.send.wizard"
    _description = "Bulk Email Send Wizard"

    template_id = fields.Many2one(
        "mail.template",
        string="Email Template",
        required=True,
    )
    # When pre-set via context (default_template_id), lock the field.
    template_locked = fields.Boolean()
    active_model = fields.Char(readonly=True)
    # Store active_ids as a JSON list since the target model is unknown at
    # definition time and cannot be expressed as a Many2many field.
    active_ids_json = fields.Char()
    record_count = fields.Integer(
        string="Records",
        compute="_compute_record_count",
    )

    @api.depends("active_ids_json")
    def _compute_record_count(self):
        for wizard in self:
            wizard.record_count = len(json.loads(wizard.active_ids_json or "[]"))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        res["active_ids_json"] = json.dumps(ctx.get("active_ids", []))
        res["active_model"] = ctx.get("active_model", "")
        if ctx.get("default_template_id"):
            res["template_locked"] = True
        return res

    def action_send(self):
        if self.template_id.model != self.active_model:
            raise ValidationError(
                _(
                    "Template model '%(template_model)s' does not match the selected "
                    "records model '%(active_model)s'."
                )
                % {
                    "template_model": self.template_id.model,
                    "active_model": self.active_model,
                }
            )
        active_ids = json.loads(self.active_ids_json or "[]")
        records = self.env[self.active_model].browse(active_ids).exists()
        sent = 0
        for record in records:
            self.template_id.send_mail(record.id, force_send=False)
            sent += 1
        return {"type": "ir.actions.act_window_close"}
