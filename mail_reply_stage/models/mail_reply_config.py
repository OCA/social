# Copyright 2025 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailReplyConfig(models.Model):
    _name = "mail.reply.config"
    _description = "Mail Reply Configuration"

    sequence = fields.Integer(default=10)
    model_id = fields.Many2one(
        "ir.model", string="Model", required=True, ondelete="cascade"
    )
    parent_field_id = fields.Many2one(
        "ir.model.fields",
        string="Parent Field",
        domain="[('model_id', '=', model_id), ('ttype', '=', 'many2one')]",
        ondelete="cascade",
    )
    parent_model_name = fields.Char(
        related="parent_field_id.relation",
        string="Parent Model",
        help="Automatically stores the model name of the related parent entity.",
    )
    parent_stage_field_id = fields.Many2one(
        "ir.model.fields",
        string="Parent Stage Field",
        domain=(
            "[('model_id.model', '=', parent_model_name), ('ttype', '=', 'many2many')]"
        ),
        ondelete="cascade",
        help="A Many2Many field within the parent model that defines "
        "valid stages for this configuration.",
    )
    domain = fields.Char(
        help="Domain used to find matching config dynamically,"
        "e.g., [('project_id.name', '=', 'My Project')]",
    )
    reply_stage_field_id = fields.Many2one(
        "ir.model.fields",
        domain="[('model_id', '=', model_id), ('ttype', '=', 'many2one')]",
        required=True,
        ondelete="cascade",
    )
    reply_stage_model_name = fields.Char(related="reply_stage_field_id.relation")
    reply_stage_xml_id = fields.Many2one(
        "ir.model.data",
        string="Reply Stage",
        help="Select the reply stage from the related model.",
    )
    reply_stage_xml_id_domain = fields.Binary(
        compute="_compute_reply_stage_xml_id_domain"
    )
    reply_stage_id = fields.Many2oneReference(
        related="reply_stage_xml_id.res_id",
        help="Technical field to store the id of reply stage.",
    )

    @api.depends("reply_stage_field_id")
    def _compute_reply_stage_xml_id_domain(self):
        for rec in self:
            if not rec.reply_stage_field_id:
                rec.reply_stage_xml_id_domain = []
                continue
            Model = self.env[rec.reply_stage_model_name]
            records = Model.search([], limit=1000)
            xml_ids = self.env["ir.model.data"].search(
                [
                    ("model", "=", rec.reply_stage_model_name),
                    ("res_id", "in", records.ids),
                ]
            )
            rec.reply_stage_xml_id_domain = [("id", "in", xml_ids.ids)]

    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.parent_field_id = False
        self.parent_stage_field_id = False
        self.reply_stage_field_id = False
        self.reply_stage_xml_id = False

    @api.onchange("parent_field_id")
    def _onchange_parent_field_id(self):
        self.parent_stage_field_id = False

    @api.onchange("reply_stage_field_id")
    def _onchange_reply_stage_field_id(self):
        self.reply_stage_xml_id = False
        if self.reply_stage_field_id:
            model_name = self.reply_stage_model_name
            xmlid_ids = (
                self.env["ir.model.data"]
                .search([("model", "=", model_name)])
                .mapped("res_id")
            )
            recs_to_export = self.env[model_name].search([("id", "not in", xmlid_ids)])
            if recs_to_export:
                recs_to_export._export_rows([["id"]])
