# Copyright 2024 Tecnativa - Carlos López
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import re
from urllib.parse import urlparse

import requests
from werkzeug.urls import url_join

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import ustr

from odoo.addons.phone_validation.tools import phone_validation

from ..tools.const import REG_VARIABLE, supported_languages
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
    model_id = fields.Many2one(
        string="Applies to",
        comodel_name="ir.model",
        default=lambda self: self.env["ir.model"]._get_id("res.partner"),
        required=True,
        ondelete="cascade",
    )
    model = fields.Char(string="Related model", related="model_id.model", store=True)
    variable_ids = fields.One2many(
        "mail.whatsapp.template.variable",
        "template_id",
        string="Variables",
        store=True,
        compute="_compute_variable_ids",
        precompute=True,
        readonly=False,
    )
    button_ids = fields.One2many(
        "mail.whatsapp.template.button", "template_id", string="Buttons"
    )

    _sql_constraints = [
        (
            "unique_name_gateway_id",
            "unique(name, language, gateway_id)",
            "Duplicate name is not allowed for Gateway.",
        )
    ]

    @api.constrains("button_ids")
    def _check_buttons(self):
        for template in self:
            if len(template.button_ids) > 10:
                raise ValidationError(self.env._("A maximum of 10 buttons is allowed."))
            url_buttons = template.button_ids.filtered(
                lambda button: button.button_type == "url"
            )
            phone_number_buttons = template.button_ids.filtered(
                lambda button: button.button_type == "phone_number"
            )
            if len(url_buttons) > 2:
                raise ValidationError(
                    self.env._("A maximum of 2 URL buttons is allowed.")
                )
            if len(phone_number_buttons) > 1:
                raise ValidationError(
                    self.env._("A maximum of 1 Call Number button is allowed.")
                )

    @api.constrains("variable_ids")
    def _check_variables(self):
        for template in self:
            body_variables = template.variable_ids.filtered(
                lambda var: var.line_type == "body"
            )
            header_variables = template.variable_ids.filtered(
                lambda var: var.line_type == "header"
            )
            if len(header_variables) > 1:
                raise ValidationError(
                    self.env._("There should be exactly 1 variable in the header.")
                )
            if header_variables and header_variables._extract_variable_index() != 1:
                raise ValidationError(
                    self.env._("Variable in the header should be used as {{1}}")
                )
            variable_indices = sorted(
                var._extract_variable_index() for var in body_variables
            )
            if len(variable_indices) > 0 and (
                variable_indices[0] != 1 or variable_indices[-1] != len(body_variables)
            ):
                missing = (
                    next(
                        (
                            index
                            for index in range(1, len(body_variables))
                            if variable_indices[index - 1] + 1
                            != variable_indices[index]
                        ),
                        0,
                    )
                    + 1
                )
                raise ValidationError(
                    self.env._(
                        "Body variables should start at 1 and not skip any number, "
                        "missing %d",
                        missing,
                    )
                )

    @api.depends("name", "state", "template_uid")
    def _compute_template_name(self):
        for template in self:
            if not template.template_name or (
                template.state == "draft" and not template.template_uid
            ):
                template.template_name = re.sub(
                    r"\W+", "_", self.env["ir.http"]._slugify(template.name or "")
                )

    @api.depends("header", "body")
    def _compute_variable_ids(self):
        for template in self:
            to_remove = self.env["mail.whatsapp.template.variable"]
            to_keep = self.env["mail.whatsapp.template.variable"]
            new_values = []
            header_variables = list(re.findall(REG_VARIABLE, template.header or ""))
            body_variables = set(re.findall(REG_VARIABLE, template.body or ""))
            # header
            current_header_variable = template.variable_ids.filtered(
                lambda line: line.line_type == "header"
            )
            if header_variables and not current_header_variable:
                new_values.append(
                    {
                        "name": header_variables[0],
                        "line_type": "header",
                        "template_id": template.id,
                    }
                )
            elif not header_variables and current_header_variable:
                to_remove += current_header_variable
            elif current_header_variable:
                to_keep += current_header_variable
            # body
            current_body_variables = template.variable_ids.filtered(
                lambda line: line.line_type == "body"
            )
            new_body_variable_names = [
                var_name
                for var_name in body_variables
                if var_name not in current_body_variables.mapped("name")
            ]
            deleted_variables = current_body_variables.filtered(
                lambda var, body_variables=body_variables: var.name
                not in body_variables
            )

            new_values += [
                {"name": var_name, "line_type": "body", "template_id": template.id}
                for var_name in set(new_body_variable_names)
            ]
            to_remove += deleted_variables
            to_keep += current_body_variables - deleted_variables
            template.variable_ids = [
                Command.unlink(to_remove.id) for to_remove in to_remove
            ] + [Command.create(vals) for vals in new_values]

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
                headers={"Authorization": f"Bearer {gateway.token}"},
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
        body_component = {"type": "BODY", "text": self.body}
        body_params = self.variable_ids.filtered(lambda line: line.line_type == "body")
        if body_params:
            body_component["example"] = {
                "body_text": [body_params.mapped("sample_value")]
            }
        components = [body_component]
        if self.header:
            header_component = {"type": "HEADER", "format": "TEXT", "text": self.header}
            header_params = self.variable_ids.filtered(
                lambda line: line.line_type == "header"
            )
            if header_params:
                header_component["example"] = {
                    "header_text": header_params.mapped("sample_value")
                }
            components.append(header_component)
        if self.footer:
            components.append({"type": "FOOTER", "text": self.footer})
        buttons = []
        for button in self.button_ids:
            button_data = {"type": button.button_type.upper(), "text": button.name}
            if button.button_type == "url":
                button_data["url"] = button.website_url
                if button.url_type == "dynamic":
                    button_data["url"] += "{{1}}"
                    button_data["example"] = button.variable_ids[0].sample_value
            elif button.button_type == "phone_number":
                button_data["phone_number"] = button.call_number
            buttons.append(button_data)
        if buttons:
            components.append({"type": "BUTTONS", "buttons": buttons})
        # TODO: add more components(location, etc)
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
                headers={"Authorization": f"Bearer {gateway.token}"},
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
            elif component["type"] == "BUTTONS":
                for index, button in enumerate(component["buttons"]):
                    if button["type"] in ("URL", "PHONE_NUMBER", "QUICK_REPLY"):
                        button_vals = {
                            "sequence": index,
                            "name": button["text"],
                            "button_type": button["type"].lower(),
                            "call_number": button.get("phone_number"),
                            "website_url": button.get("url"),
                        }
                        vals.setdefault("button_ids", [])
                        button = self.button_ids.filtered(
                            lambda btn, button=button: btn.name == button["text"]
                        )
                        if button:
                            vals["button_ids"].append(
                                Command.update(button.id, button_vals)
                            )
                        else:
                            vals["button_ids"].append(Command.create(button_vals))
            else:
                is_supported = False
        vals["is_supported"] = is_supported
        return vals

    def _prepare_header_component(self, variable_ids_value):
        header = []
        if self.header and variable_ids_value.get("header-{{1}}"):
            value = variable_ids_value.get("header-{{1}}") or (self.header or {}) or ""
            header = {"type": "header", "parameters": [{"type": "text", "text": value}]}
        return header

    def _prepare_body_components(self, variable_ids_value):
        if not self.variable_ids:
            return None
        parameters = []
        for body_val in self.variable_ids.filtered(
            lambda line: line.line_type == "body"
        ):
            parameters.append(
                {
                    "type": "text",
                    "text": variable_ids_value.get(
                        f"{body_val.line_type}-{body_val.name}"
                    )
                    or " ",
                }
            )
        return {"type": "body", "parameters": parameters}

    def _prepare_button_components(self, variable_ids_value):
        components = []
        dynamic_buttons = self.button_ids.filtered(
            lambda line: line.url_type == "dynamic"
        )
        index = {button: i for i, button in enumerate(self.button_ids)}
        for button in dynamic_buttons:
            dynamic_url = button.website_url
            value = variable_ids_value.get(f"button-{button.name}") or " "
            value = value.replace(dynamic_url, "").lstrip("/")
            components.append(
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": index.get(button),
                    "parameters": [{"type": "text", "text": value}],
                }
            )
        return components

    def prepare_value_to_send(self):
        self.ensure_one()
        model_name = self.model_id.model
        rec_id = self.env.context.get("default_res_id")
        if rec_id is None:
            rec_ids = self.env.context.get("res_id")
            if rec_ids:
                rec_id = rec_ids
            else:
                rec_id = None
        if model_name and rec_id:
            record = self.env[model_name].browse(int(rec_id))
        components = []
        variable_ids_value = self.variable_ids._get_variables_value(record)
        # generate components
        header = self._prepare_header_component(variable_ids_value=variable_ids_value)
        body = self._prepare_body_components(variable_ids_value=variable_ids_value)
        buttons = self._prepare_button_components(variable_ids_value=variable_ids_value)
        if header:
            components.append(header)
        if body:
            components.append(body)
        components.extend(buttons)
        return components

    def render_body_message(self):
        self.ensure_one()
        model_name = self.model_id.model
        rec_id = self.env.context.get("default_res_id")
        if rec_id is None:
            rec_ids = self.env.context.get("default_res_ids")
            if isinstance(rec_ids, list) and rec_ids:
                rec_id = rec_ids[0]
            else:
                rec_id = None
        if model_name and rec_id:
            record = self.env[model_name].browse(int(rec_id))
        header = ""
        if self.header:
            header = self.header
            header_vars = self.variable_ids.filtered(lambda v: v.line_type == "header")
            for i, var in enumerate(header_vars, start=1):
                placeholder = f"{{{{{i}}}}}"
                value = var._get_variables_value(record).get(
                    f"header-{placeholder}", ""
                )
                header = header.replace(placeholder, str(value))
        body = self.body or ""
        body_vars = self.variable_ids.filtered(lambda v: v.line_type == "body")
        for i, var in enumerate(body_vars, start=1):
            placeholder = f"{{{{{i}}}}}"
            value = var._get_variables_value(record).get(f"body-{placeholder}", "")
            body = body.replace(placeholder, str(value))
        message = f"*{header}*\n\n{body}" if header else body
        return message


class MailWhatsAppTemplateVariable(models.Model):
    _name = "mail.whatsapp.template.variable"
    _description = "WhatsApp Template Variable"
    _order = "line_type desc, name, id"

    name = fields.Char(string="Placeholder", required=True)
    template_id = fields.Many2one(
        comodel_name="mail.whatsapp.template", required=True, ondelete="cascade"
    )
    model = fields.Char(string="Model Name", related="template_id.model")
    line_type = fields.Selection(
        [("header", "Header"), ("body", "Body"), ("button", "Button")], required=True
    )
    field_name = fields.Char(string="Field")
    sample_value = fields.Char(default="Sample Value", required=True)
    button_id = fields.Many2one("mail.whatsapp.template.button", ondelete="cascade")

    _sql_constraints = [
        (
            "name_type_template_unique",
            "UNIQUE(name, line_type, template_id,button_id)",
            "Variable names must be unique by template",
        ),
    ]

    @api.constrains("field_name")
    def _check_field_name(self):
        failing = self.browse()
        missing = self.filtered(lambda variable: not variable.field_name)
        if missing:
            raise ValidationError(
                self.env._(
                    "Field template variables %(variables)s "
                    "must be associated with a field.",
                    variables=", ".join(missing.mapped("name")),
                )
            )
        for variable in self:
            model = self.env[variable.model]
            if not model.has_access("read"):
                model_description = (
                    self.env["ir.model"]._get(variable.model).display_name
                )
                raise ValidationError(
                    self.env._(
                        "You can not select field of %(model)s.",
                        model=model_description,
                    )
                )
            try:
                variable._extract_value_from_field_path(model)
            except UserError:
                failing += variable
        if failing:
            model_description = (
                self.env["ir.model"]._get(failing.mapped("model")[0]).display_name
            )
            raise ValidationError(
                self.env._(
                    "Variables %(field_names)s do not seem to be valid field path "
                    "for model %(model_name)s.",
                    field_names=", ".join(failing.mapped("field_name")),
                    model_name=model_description,
                )
            )

    @api.constrains("name")
    def _check_name(self):
        for variable in self:
            if not variable._extract_variable_index():
                raise ValidationError(
                    self.env._(
                        "Template variable should be in format {{number}}. "
                        "Cannot parse '%(placeholder)s'",
                        placeholder=variable.name,
                    )
                )

    @api.depends("line_type", "name")
    def _compute_display_name(self):
        type_names = dict(self._fields["line_type"]._description_selection(self.env))
        for variable in self:
            type_name = type_names[variable.line_type or "body"]
            variable.display_name = (
                type_name
                if variable.line_type == "header"
                else f"{type_name} - {variable.name}"
            )

    @api.onchange("model")
    def _onchange_model_id(self):
        self.field_name = False

    def _get_variables_value(self, record):
        value_by_name = {}
        for variable in self:
            value = variable._extract_value_from_field_path(record)
            value_str = value and str(value) or ""
            value_key = f"{variable.line_type}-{variable.name}"
            value_by_name[value_key] = value_str
        return value_by_name

    def _extract_variable_index(self):
        """Extract variable index, located between '{{}}' markers."""
        self.ensure_one()
        try:
            return int(self.name.replace("{{", "").replace("}}", ""))
        except ValueError:
            return None

    def _extract_value_from_field_path(self, record):
        field_path = self.field_name
        if not field_path:
            return ""
        try:
            field_value = record.mapped(field_path)
        except Exception as err:
            raise UserError(
                self.env._(
                    "We were not able to fetch value of field: %(field)s",
                    field=field_path,
                )
            ) from err
        if isinstance(field_value, models.Model):
            return " ".join((value.display_name or "") for value in field_value)
        # find last field / last model when having chained fields
        # e.g. 'partner_id.country_id.state' -> ['partner_id.country_id', 'state']
        field_path_models = field_path.rsplit(".", 1)
        if len(field_path_models) > 1:
            last_model_path, last_fname = field_path_models
            last_model = record.mapped(last_model_path)
        else:
            last_model, last_fname = record, field_path
        last_field = last_model._fields[last_fname]
        # return value instead of the key
        if last_field.type == "selection":
            return " ".join(
                last_field.convert_to_export(value, last_model) for value in field_value
            )
        return " ".join(
            str(value if value is not False and value is not None else "")
            for value in field_value
        )


class MailWhatsAppTemplateButton(models.Model):
    _name = "mail.whatsapp.template.button"
    _description = "WhatsApp Template Button"
    _order = "sequence,id"

    sequence = fields.Integer()
    name = fields.Char(string="Button Text", size=25)
    template_id = fields.Many2one(
        comodel_name="mail.whatsapp.template", required=True, ondelete="cascade"
    )
    button_type = fields.Selection(
        [
            ("quick_reply", "Quick Reply"),
            ("url", "Visit Website"),
            ("phone_number", "Call Number"),
        ],
        string="Type",
        required=True,
        default="quick_reply",
    )
    url_type = fields.Selection(
        [("static", "Static"), ("dynamic", "Dynamic")],
        default="static",
    )
    website_url = fields.Char()
    call_number = fields.Char()
    variable_ids = fields.One2many(
        "mail.whatsapp.template.variable",
        "button_id",
        compute="_compute_variable_ids",
        precompute=True,
        store=True,
        copy=True,
    )

    _sql_constraints = [
        (
            "unique_name_per_template",
            "UNIQUE(name, template_id)",
            "Button name must be unique by template",
        )
    ]

    @api.constrains("button_type", "url_type", "website_url")
    def _validate_website_url(self):
        for button in self.filtered(lambda button: button.button_type == "url"):
            parsed_url = urlparse(button.website_url)
            if not (parsed_url.scheme in {"http", "https"} and parsed_url.netloc):
                raise ValidationError(
                    self.env._(
                        "Please enter a valid URL in the format 'https://www.example.com'."
                    )
                )

    @api.constrains("call_number")
    def _validate_call_number(self):
        for button in self:
            if button.button_type == "phone_number":
                phone_validation.phone_format(button.call_number, False, False)

    @api.depends("button_type", "url_type", "website_url", "name")
    def _compute_variable_ids(self):
        dynamic_urls = self.filtered(
            lambda button: button.button_type == "url" and button.url_type == "dynamic"
        )
        to_clear = self - dynamic_urls
        for button in dynamic_urls:
            if button.variable_ids:
                button.variable_ids = [
                    Command.update(
                        button.variable_ids[0].id,
                        {
                            "sample_value": button.website_url,
                            "line_type": "button",
                            "name": button.name,
                            "button_id": button.id,
                            "template_id": button.template_id.id,
                        },
                    ),
                ]
            else:
                button.variable_ids = [
                    Command.create(
                        {
                            "sample_value": button.website_url,
                            "line_type": "button",
                            "name": button.name,
                            "button_id": button.id,
                            "template_id": button.template_id.id,
                        },
                    ),
                ]
        if to_clear:
            to_clear.variable_ids = [Command.clear()]

    def check_variable_ids(self):
        for button in self:
            if len(button.variable_ids) > 1:
                raise ValidationError(
                    self.env._("Buttons may only contain one placeholder.")
                )
            if button.variable_ids and button.url_type != "dynamic":
                raise ValidationError(
                    self.env._("Only dynamic urls may have a placeholder.")
                )
            elif button.url_type == "dynamic" and not button.variable_ids:
                raise ValidationError(
                    self.env._("All dynamic urls must have a placeholder.")
                )
            if button.variable_ids.name != "{{1}}":
                raise ValidationError(
                    self.env._("The placeholder for a button can only be {{1}}.")
                )
