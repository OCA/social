# Copyright 2024 Tecnativa - Carlos López
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import re

import requests
from werkzeug.urls import url_join

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import ustr

from odoo.addons.http_routing.models.ir_http import slugify

from ..tools.const import supported_languages
from .mail_gateway import BASE_URL


class MailWhatsAppTemplate(models.Model):
    _name = "mail.whatsapp.template"
    _description = "Mail WhatsApp template"

    name = fields.Char(required=True)
    body = fields.Text(required=True)
    header = fields.Char()
    footer = fields.Char()
    template_name = fields.Char(
        compute="_compute_template_name", store=True, copy=False
    )
    is_supported = fields.Boolean(copy=False)
    template_uid = fields.Char(readonly=True, copy=False)
    category = fields.Selection(
        [
            ("authentication", "Authentication"),
            ("marketing", "Marketing"),
            ("utility", "Utility"),
        ],
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("in_appeal", "In Appeal"),
            ("rejected", "Rejected"),
            ("pending_deletion", "Pending Deletion"),
            ("deleted", "Deleted"),
            ("disabled", "Disabled"),
            ("paused", "Paused"),
            ("limit_exceeded", "Limit Exceeded"),
            ("archived", "Archived"),
        ],
        default="draft",
        required=True,
    )
    language = fields.Selection(supported_languages, required=True)
    gateway_id = fields.Many2one(
        "mail.gateway",
        domain=[("gateway_type", "=", "whatsapp")],
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company", related="gateway_id.company_id", store=True
    )

    _sql_constraints = [
        (
            "unique_name_gateway_id",
            "unique(name, language, gateway_id)",
            "Duplicate name is not allowed for Gateway.",
        )
    ]

    @api.depends("name", "state", "template_uid")
    def _compute_template_name(self):
        for template in self:
            if not template.template_name or (
                template.state == "draft" and not template.template_uid
            ):
                template.template_name = re.sub(
                    r"\W+", "_", slugify(template.name or "")
                )

    def button_back2draft(self):
        self.write({"state": "draft"})

    def button_export_template(self):
        self.ensure_one()
        gateway = self.gateway_id
        template_url = url_join(
            BASE_URL,
            f"v{gateway.whatsapp_version}/{gateway.whatsapp_account_id}/message_templates",
        )
        try:
            payload = self._prepare_values_to_export()
            response = requests.post(
                template_url,
                headers={"Authorization": "Bearer %s" % gateway.token},
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            json_data = response.json()
            self.write(
                {
                    "template_uid": json_data.get("id"),
                    "state": json_data.get("status").lower(),
                    "is_supported": True,
                }
            )
        except requests.exceptions.HTTPError as ex:
            msj = f"{ustr(ex)} \n{ex.response.text}"
            raise UserError(msj) from ex
        except Exception as err:
            raise UserError(ustr(err)) from err

    def _prepare_values_to_export(self):
        components = self._prepare_components_to_export()
        return {
            "name": self.template_name,
            "category": self.category.upper(),
            "language": self.language,
            "components": components,
        }

    def _prepare_components_to_export(self):
        components = [{"type": "BODY", "text": self.body}]
        if self.header:
            components.append(
                {
                    "type": "HEADER",
                    "format": "text",
                    "text": self.header,
                }
            )
        if self.footer:
            components.append(
                {
                    "type": "FOOTER",
                    "text": self.footer,
                }
            )
        # TODO: add more components(buttons, location, etc)
        return components

    def button_sync_template(self):
        self.ensure_one()
        gateway = self.gateway_id
        template_url = url_join(
            BASE_URL,
            f"{self.template_uid}",
        )
        try:
            response = requests.get(
                template_url,
                headers={"Authorization": "Bearer %s" % gateway.token},
                timeout=10,
            )
            response.raise_for_status()
            json_data = response.json()
            vals = self._prepare_values_to_import(gateway, json_data)
            self.write(vals)
        except Exception as err:
            raise UserError(str(err)) from err
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    @api.model
    def _prepare_values_to_import(self, gateway, json_data):
        vals = {
            "name": json_data.get("name").replace("_", " ").title(),
            "template_name": json_data.get("name"),
            "category": json_data.get("category").lower(),
            "language": json_data.get("language"),
            "state": json_data.get("status").lower(),
            "template_uid": json_data.get("id"),
            "gateway_id": gateway.id,
        }
        is_supported = True
        for component in json_data.get("components", []):
            if component["type"] == "HEADER" and component["format"] == "TEXT":
                vals["header"] = component["text"]
            elif component["type"] == "BODY":
                vals["body"] = component["text"]
            elif component["type"] == "FOOTER":
                vals["footer"] = component["text"]
            else:
                is_supported = False
        vals["is_supported"] = is_supported
        return vals
