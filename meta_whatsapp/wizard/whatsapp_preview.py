from odoo import api, fields, models


class WhatsAppPreview(models.TransientModel):
    _name = "whatsapp.preview"
    _description = "WhatsApp Template Preview"

    template_id = fields.Many2one("whatsapp.template", string="Template", required=True, ondelete="cascade")
    lang = fields.Selection(lambda self: self.env['res.lang'].get_installed(), string='Template Preview Language')
    model_id = fields.Many2one("ir.model", string="Model", related="template_id.model_id")
    res_id = fields.Reference(
        string="Record",
        selection="_selection_target_model",
        required=True,
    )
    body = fields.Text(string="Body", compute="_compute_preview", readonly=True)
    header_text = fields.Char(string="Header", compute="_compute_preview", readonly=True)
    footer_text = fields.Char(string="Footer", related="template_id.footer_text", readonly=True)
    no_record = fields.Boolean("No Record", compute="_compute_no_record")

    @api.model
    def _selection_target_model(self):
        models = self.env["ir.model"].search([("is_mail_thread", "=", True)])
        return [(model.model, model.name) for model in models]

    @api.model
    def default_get(self, fields):
        res = super(WhatsAppPreview, self).default_get(fields)
        template_id = res.get("template_id") or self.env.context.get("default_template_id")
        if not res.get("res_id") and template_id:
            template = self.env["whatsapp.template"].browse(template_id)
            if template.model_id:
                record = self.env[template.model_id.model].search([], limit=1)
                if record:
                    res["res_id"] = "%s,%s" % (template.model_id.model, record.id)
        return res

    @api.depends("model_id")
    def _compute_no_record(self):
        for preview in self:
            preview.no_record = (
                self.env[preview.model_id.model].search_count([]) == 0
                if preview.model_id
                else True
            )

    @api.depends("template_id", "res_id")
    def _compute_preview(self):
        for preview in self:
            if not preview.template_id or not preview.res_id:
                preview.body = ""
                preview.header_text = ""
                continue

            template = preview.template_id
            record = preview.res_id

            body = template.body or ""
            header = template.header_text or ""

            # Simple rendering logic (reusing or centralizing this would be better)
            for var in template.variable_ids.sorted("sequence"):
                placeholder = var.name
                value = ""
                if var.field_type == "text":
                    value = var.field_name
                elif var.field_type == "field":
                    try:
                        field_path = var.field_name.split(".")
                        val = record
                        for path in field_path:
                            if not val: break
                            val = getattr(val, path, "")
                        value = str(val) if val not in (False, None) else ""
                    except Exception:
                        value = "[Error]"

                if value:
                    body = body.replace(placeholder, value)
                    header = header.replace(placeholder, value)

            preview.body = body
            preview.header_text = header
