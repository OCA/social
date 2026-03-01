import re
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WhatsAppTemplate(models.Model):
    _name = "whatsapp.template"
    _description = "WhatsApp Template"

    _sql_constraints = [
        (
            "name_lang_unique",
            "unique(name, language)",
            "Template name and language must be unique!",
        )
    ]

    name = fields.Char(string="Name", required=True)
    status = fields.Selection(
        [
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
            ("PENDING", "Pending"),
            ("PAUSED", "Paused"),
            ("DISABLED", "Disabled"),
        ],
        string="Status",
        default="PENDING",
        readonly=True,
    )

    language = fields.Char(string="Language", required=True, default="en_US")

    category = fields.Selection(
        [
            ("AUTHENTICATION", "Authentication"),
            ("MARKETING", "Marketing"),
            ("UTILITY", "Utility"),
        ],
        string="Category",
    )

    body = fields.Text(string="Body Text", translate=True)
    header_type = fields.Selection(
        [
            ("TEXT", "Text"),
            ("IMAGE", "Image"),
            ("VIDEO", "Video"),
            ("DOCUMENT", "Document"),
            ("LOCATION", "Location"),
            ("NONE", "None"),
        ],
        string="Header Type",
        default="NONE",
    )
    header_text = fields.Char(string="Header Text")
    header_media_handle = fields.Char(string="Header Media Handle")
    header_media_url = fields.Char(string="Header Media URL")
    footer_text = fields.Char(string="Footer Text")

    button_ids = fields.One2many(
        "whatsapp.template.button", "template_id", string="Buttons"
    )

    model_id = fields.Many2one(
        "ir.model",
        string="Applies to",
        domain=[("is_mail_thread", "=", True)],
        help="The type of document this template can be used with",
    )
    model_model = fields.Char(
        related="model_id.model", index=True, store=True, string="Model"
    )

    variable_ids = fields.One2many(
        "whatsapp.template.variable", "template_id", string="Variables"
    )

    sidebar_action_id = fields.Many2one(
        "ir.actions.act_window", "Sidebar Action", readonly=True, copy=False
    )

    def _get_meta_credentials(self):
        """Retrieve Meta API credentials from settings."""
        params = self.env["ir.config_parameter"].sudo()
        api_url = (params.get_param("meta_whatsapp.api_url") or "").strip()
        api_version = (params.get_param("meta_whatsapp.api_version") or "").strip()
        access_token = (params.get_param("meta_whatsapp.access_token") or "").strip()

        # Remove any invisible characters or spaces within the token
        if access_token:
            # Remove whitespace and common invisible Unicode characters
            access_token = "".join(access_token.split())
            if access_token.startswith("Bearer "):
                access_token = access_token[7:].strip()

        waba_id = (params.get_param("meta_whatsapp.waba_id") or "").strip()

        if not all([api_url, api_version, access_token, waba_id]):
            raise UserError(_("Please configure Meta WhatsApp settings first."))

        # Remove trailing slash from URL if present
        if api_url.endswith("/"):
            api_url = api_url[:-1]

        return api_url, api_version, access_token, waba_id

    def action_sync_templates(self):
        """Sync templates from Meta Business Account."""
        api_url, api_version, access_token, waba_id = self._get_meta_credentials()

        url = f"{api_url}/{api_version}/{waba_id}/message_templates"
        params = {
            "access_token": access_token,
            "limit": 100,  # Get up to 100 templates
        }

        try:
            response = requests.get(url, params=params, timeout=30)
        except Exception as e:
            raise UserError(_("Connection Error: %s") % str(e))

        if response.status_code != 200:
            error_msg = response.text
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", error_msg)
            except Exception:
                pass
            raise UserError(_("Meta API Error: %s") % error_msg)

        data = response.json()

        # Get list of active languages in Odoo to avoid ValueError
        # We search for all installed languages.
        active_langs = [l.code for l in self.env["res.lang"].sudo().search([])]

        for tmpl_data in data.get("data", []):
            existing = self.search(
                [
                    ("name", "=", tmpl_data["name"]),
                    ("language", "=", tmpl_data["language"]),
                ],
                limit=1,
            )

            vals = {
                "name": tmpl_data["name"],
                "status": tmpl_data["status"],
                "category": tmpl_data["category"],
                "language": tmpl_data["language"],
                "body": False,
                "header_text": False,
                "footer_text": False,
                "header_type": "NONE",
                "header_media_handle": False,
                "header_media_url": False,
            }

            # Extended parsing of components to update body/header/footer
            body_text = ""
            header_text = ""
            footer_text = ""
            buttons_data = []

            for component in tmpl_data.get("components", []):
                ctype = component.get("type", "").upper()
                if ctype == "BODY":
                    body_text = component.get("text", "")
                    vals["body"] = body_text
                elif ctype == "HEADER":
                    vals["header_type"] = component.get("format", "TEXT")
                    if vals["header_type"] == "TEXT":
                        header_text = component.get("text", "")
                        vals["header_text"] = header_text
                    elif vals["header_type"] in ["IMAGE", "VIDEO", "DOCUMENT"]:
                        example = component.get("example", {})
                        header_handles = example.get("header_handle", [])
                        if header_handles:
                            vals["header_media_handle"] = header_handles[0]
                        header_urls = example.get("header_url", [])
                        if header_urls:
                             vals["header_media_url"] = header_urls[0]

                elif ctype == "FOOTER":
                    footer_text = component.get("text", "")
                    vals["footer_text"] = footer_text
                elif ctype == "BUTTONS":
                    for btn in component.get("buttons", []):
                        btn_type = btn.get("type", "").upper()
                        btn_vals = {
                            "type": btn_type,
                            "text": btn.get("text", ""),
                        }
                        if btn_type == "URL":
                            btn_vals["website_url"] = btn.get("url", "")
                            if "{{" in btn_vals["website_url"]:
                                btn_vals["url_type"] = "DYNAMIC"
                            else:
                                btn_vals["url_type"] = "STATIC"
                        elif btn_type == "PHONE_NUMBER":
                            btn_vals["phone_number"] = btn.get("phone_number", "")

                        buttons_data.append(btn_vals)

            # Set context language if it is active in Odoo, else use current context
            lang_code = tmpl_data["language"]
            if lang_code not in active_langs:
                # Meta uses underscores (pt_BR), Odoo might use underscores too,
                # but sometimes there are slight differences.
                # If still not found, try to find the closest match or just skip translation context
                lang_code = self.env.context.get("lang")

            ctx = dict(self.env.context, lang=lang_code)

            if existing:
                # Update existing record with correct language context
                existing.with_context(ctx).write(vals)
                template = existing
            else:
                # Create new record with correct language context
                template = self.with_context(ctx).create(vals)

            # Sync buttons
            template.button_ids.unlink()
            for i, btn_vals in enumerate(buttons_data):
                btn_vals["template_id"] = template.id
                btn_vals["sequence"] = i
                btn_obj = self.env["whatsapp.template.button"].create(btn_vals)
                
                # If dynamic URL, create a variable for it
                if btn_vals.get("url_type") == "DYNAMIC":
                    # For dynamic URLs, the {{1}} is always at the end of the URL
                    # Meta usually provides it as {{1}} in the text or URL
                    var_name = "{{1}}" # Always 1 for each button
                    existing_var = self.env["whatsapp.template.variable"].search([
                        ("template_id", "=", template.id),
                        ("name", "=", var_name),
                        ("location", "=", "button"),
                        ("button_index", "=", i)
                    ])
                    if not existing_var:
                         self.env["whatsapp.template.variable"].create({
                            "template_id": template.id,
                            "name": var_name,
                            "sequence": i, # Button index
                            "location": "button",
                            "button_index": i,
                            "field_type": "field",
                            "field_name": "id",
                        })

            # Automatically extract variables {{1}}, {{2}}... from body and header
            if header_text:
                h_vars = re.findall(r"\{\{(\d+)\}\}", header_text)
                for var_num in h_vars:
                    var_name = "{{%s}}" % var_num
                    existing_var = self.env["whatsapp.template.variable"].search(
                        [("template_id", "=", template.id), ("name", "=", var_name)]
                    )
                    if not existing_var:
                        self.env["whatsapp.template.variable"].create(
                            {
                                "template_id": template.id,
                                "name": var_name,
                                "sequence": int(var_num),
                                "location": "header",
                                "field_type": "field",
                                "field_name": "id",
                            }
                        )

            if body_text:
                b_vars = re.findall(r"\{\{(\d+)\}\}", body_text)
                for var_num in b_vars:
                    var_name = "{{%s}}" % var_num
                    # Check if already created in header (some templates share numbers, but unusual)
                    existing_var = self.env["whatsapp.template.variable"].search([
                        ("template_id", "=", template.id),
                        ("name", "=", var_name)
                    ])
                    if not existing_var:
                        self.env["whatsapp.template.variable"].create(
                            {
                                "template_id": template.id,
                                "name": var_name,
                                "sequence": int(var_num),
                                "location": "body",
                                "field_type": "field",
                                "field_name": "id",
                            }
                        )

        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def action_create_sidebar_action(self):
        """Create a sidebar action for the template."""
        self.ensure_one()
        if not self.model_id:
            return

        act_window = self.env["ir.actions.act_window"].create(
            {
                "name": _("Send WhatsApp: %s") % self.name,
                "res_model": "whatsapp.composer",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_template_id": self.id,
                    "default_res_model": self.model_id.model,
                    "default_res_ids": "active_ids",
                },
                "binding_model_id": self.model_id.id,
                "binding_view_types": "list,form",
            }
        )
        self.sidebar_action_id = act_window

    def action_unlink_sidebar_action(self):
        """Remove the sidebar action."""
        self.ensure_one()
        if self.sidebar_action_id:
            self.sidebar_action_id.unlink()


class WhatsAppTemplateVariable(models.Model):
    _name = "whatsapp.template.variable"
    _description = "WhatsApp Template Variable"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "whatsapp.template", string="Template", required=True, ondelete="cascade"
    )
    name = fields.Char(string="Parameter", required=True, help="e.g. {{1}}, {{2}}")
    sequence = fields.Integer(string="Sequence", default=10)
    field_type = fields.Selection(
        [("field", "Field"), ("text", "Static Text")],
        string="Type",
        default="field",
        required=True,
    )
    location = fields.Selection(
        [("header", "Header"), ("body", "Body"), ("button", "Button")],
        string="Location",
        default="body",
        required=True,
    )
    button_index = fields.Integer(string="Button Index", default=0)
    field_name = fields.Char(
        string="Field / Text",
        required=True,
        help="Field name (e.g. partner_id.name) or static text",
    )

    demo_value = fields.Char(string="Demo Value", help="Value used for preview/testing")


class WhatsAppTemplateButton(models.Model):
    _name = "whatsapp.template.button"
    _description = "WhatsApp Template Button"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "whatsapp.template", string="Template", required=True, ondelete="cascade"
    )
    type = fields.Selection(
        [
            ("PHONE_NUMBER", "Phone Number"),
            ("URL", "URL"),
            ("QUICK_REPLY", "Quick Reply"),
            ("COPY_CODE", "Copy Code"),
        ],
        string="Type",
        required=True,
    )
    text = fields.Char(string="Button Text", required=True)
    url_type = fields.Selection(
        [("STATIC", "Static"), ("DYNAMIC", "Dynamic")],
        string="URL Type",
        default="STATIC",
    )
    website_url = fields.Char(string="Website URL")
    phone_number = fields.Char(string="Phone Number")
    sequence = fields.Integer(string="Sequence", default=10)
