# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.http import request


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def _get_allowed_mimetypes(self, company_id, res_model=None):
        if res_model:
            model = (
                self.env["ir.model"].sudo().search([("model", "=", res_model)], limit=1)
            )
            if model and model.attachment_allowed_mimetypes:
                return [
                    mt.strip().lower()
                    for mt in model.attachment_allowed_mimetypes.split(",")
                    if mt.strip()
                ]
        company = self.env["res.company"].sudo().browse(company_id)
        global_mimetypes = company.attachment_allowed_mimetypes
        if not global_mimetypes:
            return []
        return [mt.strip().lower() for mt in global_mimetypes.split(",") if mt.strip()]

    @api.model
    def _resolve_attachment_company_id(self, vals):
        company_id = vals.get("company_id")
        if company_id:
            return company_id
        res_model = vals.get("res_model")
        res_id = vals.get("res_id")
        if res_model and res_id and res_model in self.env:
            record = self.env[res_model].sudo().browse(res_id).exists()
            if record and "company_id" in record._fields and record.company_id:
                return record.company_id.id
        return self.env.company.id

    def _validate_mimetype_from_vals(self, vals):
        if self.env.context.get("install_mode"):
            return
        # Skip framework-generated assets: compiled bundles (detected at create
        # by res_model='ir.ui.view' + public=True, since their /web/assets/ url
        # is only set in a later write) and customized scss/js overrides (which
        # set url at create time).
        if (vals.get("res_model") == "ir.ui.view" and vals.get("public")) or vals.get(
            "url"
        ):
            return
        mimetype = self._compute_mimetype(vals)
        res_model = vals.get("res_model")
        company_id = self._resolve_attachment_company_id(vals)
        allowed_mimetypes = self._get_allowed_mimetypes(company_id, res_model)
        if not allowed_mimetypes:
            return
        if mimetype.lower() not in allowed_mimetypes:
            message = _("File type '%s' is not allowed.") % mimetype
            if request:
                request.mimetype_error = message
            raise ValidationError(message)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._validate_mimetype_from_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        fields_to_check = ["datas", "raw", "mimetype", "res_model", "company_id"]
        if any(key in vals for key in fields_to_check):
            for record in self:
                check_vals = {
                    "datas": vals.get("datas"),
                    "raw": vals.get("raw"),
                    "mimetype": vals.get("mimetype", record.mimetype),
                    "res_model": vals.get("res_model", record.res_model),
                    "res_id": vals.get("res_id", record.res_id),
                    "url": vals.get("url", record.url),
                    "company_id": vals.get(
                        "company_id",
                        record.company_id.id if record.company_id else False,
                    ),
                }
                self._validate_mimetype_from_vals(check_vals)
        return super().write(vals)
