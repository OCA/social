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
    header_media_url = fields.Char(string="Header Media URL", compute="_compute_preview", readonly=True)
    footer_text = fields.Char(string="Footer", related="template_id.footer_text", readonly=True)
    no_record = fields.Boolean("No Record", compute="_compute_no_record")
    preview_button_ids = fields.One2many(
        "whatsapp.preview.button", "preview_id", string="Buttons", compute="_compute_preview"
    )

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
                preview.header_media_url = ""
                preview.preview_button_ids = [(5, 0, 0)]
                continue

            template = preview.template_id
            record = preview.res_id

            body = template.body or ""
            header = template.header_text or ""
            header_media_url = template.header_media_url or ""

            # Simple rendering logic (reusing or centralizing this would be better)
            # We must use the same logic as in whatsapp_message to be consistent
            
            # 1. Header Variables (Text Only)
            if template.header_type == "TEXT":
                 h_vars = template.variable_ids.filtered(lambda v: v.location == "header").sorted("sequence")
                 for var in h_vars:
                    value = self._get_var_value(var, record)
                    header = header.replace(var.name, value)
            
            # 2. Body Variables
            b_vars = template.variable_ids.filtered(lambda v: v.location == "body").sorted("sequence")
            for var in b_vars:
                value = self._get_var_value(var, record)
                body = body.replace(var.name, value)

            preview.body = body
            preview.header_text = header
            preview.header_media_url = header_media_url

            # 3. Button Preview
            buttons_vals = []
            for i, button in enumerate(template.button_ids):
                text = button.text
                if button.url_type == "DYNAMIC":
                    btn_vars = template.variable_ids.filtered(lambda v: v.location == "button" and v.button_index == i).sorted("sequence")
                    if btn_vars:
                         value = self._get_var_value(btn_vars[0], record)
                         text += " (%s%s)" % (button.website_url or "", value)
                elif button.type == "URL":
                     text += " (%s)" % (button.website_url or "")
                elif button.type == "PHONE_NUMBER":
                     text += " (%s)" % (button.phone_number or "")
                
                buttons_vals.append((0, 0, {"text": text}))
            
            preview.preview_button_ids = buttons_vals

    def _get_var_value(self, var, record):
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
        return value


class WhatsAppPreviewButton(models.TransientModel):
    _name = "whatsapp.preview.button"
    _description = "WhatsApp Preview Button"

    preview_id = fields.Many2one("whatsapp.preview", string="Preview")
    text = fields.Char(string="Button Content")
