import logging
import re

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WhatsAppMessage(models.Model):
    _name = "whatsapp.message"
    _description = "WhatsApp Message"
    _rec_name = "body"
    _order = "id desc"

    body = fields.Text(string="Message Body")
    mobile_number = fields.Char(string="Mobile Number", required=True)
    partner_id = fields.Many2one("res.partner", string="Contact")

    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("sending", "Sending"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("read", "Read"),
            ("failed", "Failed"),
            ("canceled", "Canceled"),
        ],
        string="Status",
        default="draft",
        readonly=True,
    )

    msg_id = fields.Char(string="Message ID", readonly=True)
    failure_type = fields.Selection(
        [
            ("unknown", "Unknown"),
            ("invalid_number", "Invalid Number"),
            ("server_error", "Server Error"),
        ],
        string="Failure Type",
    )
    failure_reason = fields.Text(string="Failure Reason", readonly=True)

    template_id = fields.Many2one("whatsapp.template", string="Template")

    res_model = fields.Char(string="Related Model")
    res_id = fields.Integer(string="Related Record ID")
    
    components_json = fields.Text(string="Components JSON Override", help="If provided, overrides the automatically generated components list for the template.")

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if self.template_id and not self.body:
            self.body = self.template_id.body

    @api.model
    def create(self, vals):
        if vals.get("template_id") and not vals.get("body"):
            template = self.env["whatsapp.template"].browse(vals["template_id"])
            vals["body"] = template.body
        return super(WhatsAppMessage, self).create(vals)

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

        phone_number_id = (params.get_param("meta_whatsapp.phone_number_id") or "").strip()

        if not all([api_url, api_version, access_token, phone_number_id]):
            raise UserError(_("Please configure Meta WhatsApp settings first."))

        # Remove trailing slash from URL if present
        if api_url.endswith("/"):
            api_url = api_url[:-1]

        return api_url, api_version, access_token, phone_number_id

    def _sanitize_phone(self, phone):
        """Sanitize phone number for Meta API (digits only, no +)."""
        if not phone:
            return False
        return re.sub(r"\D", "", phone)

    def action_send(self):
        """Send the message via Meta API."""
        (
            api_url,
            api_version,
            access_token,
            phone_number_id,
        ) = self._get_meta_credentials()

        url = f"{api_url}/{api_version}/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        for msg in self:
            msg._send_message(url, headers)

    def _prepare_template_parameters(self, location="body", button_index=0):
        self.ensure_one()
        parameters = []
        if not self.template_id:
            return parameters

        record = False
        if self.res_model and self.res_id:
            record = self.env[self.res_model].browse(self.res_id)

        # Filter variables by location and sort them
        vars_to_process = self.template_id.variable_ids.filtered(
            lambda v: v.location == location and (location != "button" or v.button_index == button_index)
        ).sorted("sequence")

        for variable in vars_to_process:
            value = ""
            if variable.field_type == "text":
                value = variable.field_name
            elif variable.field_type == "field" and record:
                try:
                    # Evaluate dotted field paths (e.g. partner_id.name)
                    field_path = variable.field_name.split(".")
                    val = record
                    for path in field_path:
                        if not val:
                            break
                        # Handle fields that might be False/None
                        val = getattr(val, path, "")

                    # Formatting based on field type could be added here
                    value = str(val) if val not in (False, None) else ""
                except Exception:
                    value = ""

            # Ensure we don't send an empty string if it's required
            if not value:
                value = " "

            # Button variables are always type 'text' (for URL suffix)
            parameters.append({"type": "text", "text": value})
        return parameters

    def _send_message(self, url, headers):
        self.ensure_one()
        if self.status not in ["draft", "failed"]:
            return

        clean_phone = self._sanitize_phone(self.mobile_number)
        if not clean_phone:
            self.write({"status": "failed", "failure_type": "invalid_number"})
            return

        self.write({"status": "sending"})

        # Build components list dynamically
        components = []
        rendered_body = self.template_id.body
        rendered_header = self.template_id.header_text
        import json
        if self.components_json:
            try:
                components = json.loads(self.components_json)
            except Exception as e:
                _logger.error("Failed to parse components_json: %s", e)
        else:
            # Check for Header parameters (Text or Media)
            header_params = []
            if self.template_id.header_type == "TEXT":
                header_params = self._prepare_template_parameters(location="header")
            elif self.template_id.header_type in ["IMAGE", "VIDEO", "DOCUMENT"]:
                media_type = self.template_id.header_type.lower()
                media_vals = {}
                if self.template_id.header_media_url:
                    media_vals = {"link": self.template_id.header_media_url}
                elif self.template_id.header_media_handle:
                    media_vals = {"id": self.template_id.header_media_handle}
                
                if media_vals:
                    header_params.append({
                        "type": media_type,
                        media_type: media_vals
                    })

            if header_params:
                components.append({
                    "type": "header",
                    "parameters": header_params
                })
                if self.template_id.header_type == "TEXT":
                    for i, p in enumerate(header_params, 1):
                        placeholder = "{{%s}}" % i
                        if rendered_header:
                            rendered_header = rendered_header.replace(placeholder, p.get("text", ""))

            # Check for Body parameters
            body_params = self._prepare_template_parameters(location="body")
            if body_params:
                components.append({
                    "type": "body",
                    "parameters": body_params
                })
                for i, p in enumerate(body_params, 1):
                    placeholder = "{{%s}}" % i
                    if rendered_body:
                        rendered_body = rendered_body.replace(placeholder, p.get("text", ""))

            # Check for Button parameters (Dynamic URL buttons)
            for i, button in enumerate(self.template_id.button_ids):
                if button.url_type == "DYNAMIC":
                    btn_params = self._prepare_template_parameters(location="button", button_index=i)
                    if btn_params:
                        components.append({
                            "type": "button",
                            "sub_type": "url",
                            "index": i,
                            "parameters": btn_params
                        })

        # Final rendered text for internal Odoo logs
        full_rendered_text = ""
        if rendered_header:
            full_rendered_text += rendered_header + "\n"
        full_rendered_text += rendered_body
        
        if self.template_id.footer_text:
            full_rendered_text += "\n\n" + self.template_id.footer_text

        for i, button in enumerate(self.template_id.button_ids):
            btn_text = button.text
            if button.url_type == "DYNAMIC":
                btn_params = self._prepare_template_parameters(location="button", button_index=i)
                if btn_params:
                    # In preview, show the first parameter appended to URL
                    btn_text += " (%s%s)" % (button.website_url or "", btn_params[0].get("text", ""))
            elif button.type == "URL":
                btn_text += " (%s)" % (button.website_url or "")
            elif button.type == "PHONE_NUMBER":
                btn_text += " (%s)" % (button.phone_number or "")
            
            full_rendered_text += "\n\n[Button: %s]" % btn_text

        payload = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": self.template_id.name,
                "language": {"code": self.template_id.language},
                "components": components,
            },
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()

            if response.status_code == 200:
                self.write(
                    {
                        "status": "sent",
                        "msg_id": data.get("messages", [{}])[0].get("id"),
                        "failure_reason": False,
                        "body": full_rendered_text,
                    }
                )
            else:
                error_data = data.get("error", {})
                error_msg = error_data.get("message") or response.text
                _logger.error("Meta API Error: %s", error_msg)
                self.write(
                    {
                        "status": "failed",
                        "failure_type": "server_error",
                        "failure_reason": error_msg,
                    }
                )
        except Exception as e:
            _logger.exception("Failed to send WhatsApp message")
            self.write(
                {
                    "status": "failed",
                    "failure_type": "unknown",
                    "failure_reason": str(e)
                }
            )

    def action_retry(self):
        self.action_send()

    def action_cancel(self):
        self.write({"status": "canceled"})
