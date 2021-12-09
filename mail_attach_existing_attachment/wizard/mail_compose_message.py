# Copyright 2015 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if (
            res.get("res_id")
            and res.get("model")
            and res.get("composition_mode", "") != "mass_mail"
            and not res.get("can_attach_attachment")
        ):
            res["can_attach_attachment"] = True  # pragma: no cover
        return res

    can_attach_attachment = fields.Boolean()
    object_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="mail_compose_message_ir_attachments_object_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Object Attachments",
    )

    def get_mail_values(self, res_ids):
        res = super().get_mail_values(res_ids)
        if self.object_attachment_ids.ids and self.model and len(res_ids) == 1:
            res[res_ids[0]].setdefault("attachment_ids", []).extend(
                self.object_attachment_ids.ids
            )
        return res
