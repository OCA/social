# Copyright 2021 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from lxml import etree

from odoo import api, models, tools


class MailActivityMixin(models.AbstractModel):
    _inherit = "mail.activity.mixin"

    def read(self, fields=None, load="_classic_read"):
        """Inject fields for conditional button visibility"""
        virtual_fields = {
            fieldname
            for fieldname in fields or []
            if fieldname.startswith(self._mail_activity_predefined_fieldname())
        }
        nonvirtual_fields = list(set(fields or []) - virtual_fields)

        result = super().read(fields=nonvirtual_fields, load=load)

        if not virtual_fields:
            return result

        for this_data in result:
            for virtual_field in virtual_fields:
                activity_type_id = virtual_field[
                    len(self._mail_activity_predefined_fieldname()) :
                ]
                activity_type = self.env["mail.activity.type"].browse(
                    int(activity_type_id)
                )
                this_data[virtual_field] = self._mail_activity_predefined_condition(
                    activity_type
                )
        return result

    @api.model
    def fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False,
    ):
        """Inject buttons for predefined mail activities"""
        result = super().fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu,
        )
        if view_type != "form" or not self.env.user.has_group(
            "mail_activity_predefined.group_mail_activity_predefined"
        ):
            return result

        predefined_activities = self.env["mail.activity.type"].search(
            [
                ("predefined", "=", True),
                "|",
                ("res_model_id", "=", False),
                (
                    "res_model_id",
                    "=",
                    self.env["ir.model"].search([("model", "=", self._name)]).id,
                ),
            ]
        )
        if not predefined_activities:
            return result

        arch = etree.fromstring(result["arch"])
        for container in (
            arch.xpath("//header")
            or arch.xpath("//div[hasclass('oe_button_box')]")
            or arch.xpath(".")
        ):
            for activity in predefined_activities:
                button = self._mail_activity_predefined_button(activity, container)
                self._mail_activity_predefined_add_button(button, container)
                self._mail_activity_predefined_add_field(result, container, activity)
        result["arch"] = etree.tostring(arch)
        return result

    def _update_cache(self, values, validate=True):
        """Don't confuse the cache with our virtual fields"""
        nonvirtual_values = {
            fieldname: value
            for fieldname, value in values.items()
            if not fieldname.startswith(self._mail_activity_predefined_fieldname())
        }
        return super()._update_cache(nonvirtual_values, validate=validate)

    def _mail_activity_predefined_button(self, activity_type, container):
        """Create a button for activity_type in container"""
        return etree.Element(
            "button",
            {
                "type": "object",
                "name": "mail_activity_predefined_execute",
                "string": activity_type.name,
                "help": activity_type.summary or "",
                "context": "{'mail_activity_type_id': %d}" % (activity_type.id,),
                "modifiers": '{"invisible": [["%s", "=", false]]}'
                % (self._mail_activity_predefined_fieldname(activity_type),),
                "data-mail-activity-type": str(activity_type.id),
                "icon": activity_type.icon,
            },
        )

    def _mail_activity_predefined_add_button(self, button, container):
        """Add button to container"""
        for node in container.xpath("./button[last()]"):
            # add after all buttons
            node.addnext(button)
            break
        else:
            # but before anything else if there are no buttons
            container.insert(0, button)

    def _mail_activity_predefined_fieldname(self, activity_type=None):
        """Generate the name of a virtual field for conditional button
        visibility"""
        return "mail_activity_predefined_visible_%s" % (
            activity_type and activity_type.id or ""
        )

    def _mail_activity_predefined_add_field(
        self, result, container, activity_type,
    ):
        """Add invisible field to container for conditional button
        visibility, add field definition to result['fields']"""
        fieldname = self._mail_activity_predefined_fieldname(activity_type)
        result["fields"][fieldname] = {
            "type": "boolean",
            "change_default": False,
            "company_dependent": False,
            "depends": (),
            "group_operator": "sum",
            "help": "",
            "manual": False,
            "readonly": True,
            "required": False,
            "searchable": False,
            "sortable": False,
            "store": False,
            "string": activity_type.name,
            "views": {},
        }
        etree.SubElement(
            container,
            "field",
            {
                "name": fieldname,
                "invisible": "1",
                "readonly": "1",
                "modifiers": '{"invisible": true, "readonly": true}',
            },
        )

    def mail_activity_predefined_execute(self):
        """Apply a predefined activity type to self, type is passed in context
        key mail_activity_type_id"""
        type_id = self.env.context.get("mail_activity_type_id")
        assert type_id, "No mail_activity_type_id in context"
        return self.activity_schedule(activity_type_id=type_id)

    def _mail_activity_predefined_condition_eval_context(self, activity_type):
        """Return the evaluation context for a condition"""
        return {
            "env": self.env,
            "record": self,
        }

    def _mail_activity_predefined_condition(self, activity_type):
        """Evaluate if and activity of type activity type can be applied to
        self"""
        if not activity_type.predefined_condition:
            return True
        return tools.safe_eval(
            activity_type.predefined_condition,
            self._mail_activity_predefined_condition_eval_context(activity_type),
        )
