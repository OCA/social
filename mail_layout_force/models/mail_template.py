# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    force_email_layout_id = fields.Many2one(
        comodel_name="ir.ui.view",
        string="Force Layout",
        domain=[("type", "=", "qweb"), ("mode", "=", "primary")],
        context={"default_type": "qweb"},
        help="Force a mail layout for this template.",
    )

    def _ensure_force_email_layout_xml_id(self):
        missing = self.force_email_layout_id.filtered(lambda rec: not rec.xml_id)
        if missing:
            vals = [
                {
                    "module": "__export__",
                    "name": "force_email_layout_%s" % rec.id,
                    "model": rec._name,
                    "res_id": rec.id,
                }
                for rec in missing
            ]
            self.env["ir.model.data"].sudo().create(vals)
            self.force_email_layout_id.invalidate_cache(["xml_id"])

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_force_email_layout_xml_id()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "force_email_layout_id" in vals:
            self._ensure_force_email_layout_xml_id()
        return res
