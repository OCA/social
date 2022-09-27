# Copyright 2018-2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json

from odoo import api, fields, models


class MailTrackingValue(models.Model):

    _inherit = "mail.tracking.value"

    new_value_formatted = fields.Char(
        compute="_compute_formatted_value", string="New value"
    )
    old_value_formatted = fields.Char(
        compute="_compute_formatted_value", string="Old value"
    )
    record_name = fields.Char(related="mail_message_id.record_name")
    model = fields.Char(related="mail_message_id.model", store="True", string="Model")

    @api.depends(
        "new_value_char",
        "new_value_integer",
        "new_value_float",
        "new_value_text",
        "new_value_datetime",
        "new_value_monetary",
        "old_value_char",
        "old_value_integer",
        "old_value_float",
        "old_value_text",
        "old_value_datetime",
        "old_value_monetary",
    )
    def _compute_formatted_value(self):
        """Sets the value formatted field used in the view"""
        for record in self:
            if record.field_type in ("many2many", "one2many", "char"):
                record.new_value_formatted = record.new_value_char
                record.old_value_formatted = record.old_value_char
            elif record.field_type == "integer":
                record.new_value_formatted = str(record.new_value_integer)
                record.old_value_formatted = str(record.old_value_integer)
            elif record.field_type == "float":
                record.new_value_formatted = str(record.new_value_float)
                record.old_value_formatted = str(record.old_value_float)
            elif record.field_type == "monetary":
                record.new_value_formatted = str(record.new_value_monetary)
                record.old_value_formatted = str(record.old_value_monetary)
            elif record.field_type == "datetime":
                record.new_value_formatted = str(record.new_value_datetime)
                record.old_value_formatted = str(record.old_value_datetime)
            elif record.field_type == "text":
                record.new_value_formatted = record.new_value_text
                record.old_value_formatted = record.old_value_text

    @api.model
    def create_tracking_values(
        self,
        initial_value,
        new_value,
        col_name,
        col_info,
        tracking_sequence,
        model_name,
    ):
        """Add tacking capabilities for many2many and one2many fields"""
        if col_info["type"] in ("many2many", "one2many"):

            def get_values(source, prefix):
                if source:
                    names = ", ".join(source.exists().mapped("display_name"))
                    json_ids = json.dumps(source.ids)
                else:
                    names = ""
                    json_ids = json.dumps([])
                return {
                    "{}_value_char".format(prefix): names,
                    "{}_value_text".format(prefix): json_ids,
                }

            field = self.env["ir.model.fields"]._get(model_name, col_name)
            if not field:
                return

            values = {
                "field": field.id,
                "field_desc": col_info["string"],
                "field_type": col_info["type"],
            }
            values.update(get_values(initial_value, "old"))
            values.update(get_values(new_value, "new"))
            return values
        else:
            return super().create_tracking_values(
                initial_value,
                new_value,
                col_name,
                col_info,
                tracking_sequence,
                model_name,
            )
