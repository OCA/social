# Copyright 2021 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import itertools

from lxml import html as lxml_html

from odoo import _, api, exceptions, models, tools
from odoo.tools import mail
from odoo.tools.safe_eval import _BUILTINS


class ModelProxy(object):
    """ A wrapper for Odoo models that only exposes fields """

    def __init__(self, model):
        self.__model__ = model

    def __getattribute__(self, name):
        model = object.__getattribute__(self, "__model__")
        if name in model._fields:
            field = model._fields[name]
            value = model[name]
            if field.relational:
                value = ModelProxy(value)
            return value
        # TODO: also allow functions with some decorator set
        raise AttributeError(name)

    def __getitem__(self, key):
        if isinstance(key, str):
            return getattr(self, key)
        return ModelProxy(object.__getattribute__(self, "__model__")[key])


class MailActivity(models.Model):
    _inherit = "mail.activity"
    _mail_activity_form_prefix = "data-form-"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Apply computations in note, check for template
        """
        result = super().create(vals_list)
        for this in result:
            if not this.activity_type_id.uses_forms:
                continue
            this._mail_activity_form_assert_template()
            this._mail_activity_form_compute()
        return result

    def write(self, vals):
        """
        Apply computations in note, check for template
        """
        result = super().write(vals)
        if (
            "note" in vals
            and self.env.context.get("_mail_activity_form_compute") != self
        ):
            for this in self:
                if not this.activity_type_id.uses_forms:
                    continue
                this._mail_activity_form_assert_template()
                this._mail_activity_form_compute()
        return result

    def read(self, fields=None, load="_classic_read"):
        """
        Update note from template if we're told so
        """
        result = super().read(fields=fields, load=load)

        if (
            not fields
            or "note" in fields
            and self.env.context.get("_mail_activity_form_update") != self
        ):
            for this, this_values in zip(
                self.with_context(_mail_activity_form_update=self), result,
            ):
                activity_type = this.activity_type_id
                if (
                    not activity_type.uses_forms
                    or this.write_date > activity_type.write_date
                ):
                    continue
                # if the type has been updated, return html from type
                # but with values from current activity
                fromstring = lxml_html.fromstring
                template = fromstring(activity_type.default_description)
                current = fromstring(this_values["note"])
                this_values["note"] = lxml_html.tostring(
                    this._mail_activity_form_update(
                        template, this._mail_activity_form_extract(current),
                    ),
                ).decode("utf8")
        return result

    def _mail_activity_form_compute(self, raise_on_error=True):
        """
        Compute computed nodes and write the result to the note field
        """
        self.ensure_one()
        if not self.note:
            return
        _id, _editable, _compute, _type = self._mail_activity_form_attributes()
        doc = lxml_html.fromstring(self.note)
        vals = self._mail_activity_form_extract(doc, compute=True)
        for node in doc.xpath("//*[@%s]" % _compute):
            if node.get(_id) in vals:
                node.text = str(vals.get(node.get(_id)))
            else:
                node.text = str(
                    self._mail_activity_form_extract_value(node, vals, compute=True,)
                )
        self.with_context(_mail_activity_form_compute=self,).write(
            {"note": lxml_html.tostring(doc)}
        )

    def _mail_activity_form_assert_template(self):
        """
        Compare notes with activity_type_id.default_description and be
        sure only editable nodes have been changed
        """
        if not self.note or not self.activity_type_id.default_description:
            return
        template_html = lxml_html.fromstring(self.activity_type_id.default_description)
        activity_html = lxml_html.fromstring(
            self.with_context(_mail_activity_form_update=self).note
        )
        _id, _editable, _compute, _type = self._mail_activity_form_attributes()
        different = False
        for t, a in itertools.zip_longest(template_html.iter(), activity_html.iter()):
            if a is None or t is None or t.tag != a.tag:
                different = True
                break

            if set(t.attrib.keys()) != set(a.attrib.keys()):
                different = True
                break

            for attribute in t.attrib:
                if t.attrib[attribute].strip() != a.attrib[attribute].strip():
                    different = True

            if different:
                break

            if (t.text or "").strip() != (a.text or "").strip():
                if t.attrib.get(_compute):
                    continue
                if t.attrib.get(_editable, "").lower() not in ("1", "true"):
                    different = True
                    break

        if different:
            raise exceptions.UserError(
                _("You are not supposed to change the content of this activity.")
            )

    def _mail_activity_form_attributes(self):
        """
        Return a tuple of the attribute names constructed with the above prefix
        """
        return (
            "%sid" % self._mail_activity_form_prefix,
            "%seditable" % self._mail_activity_form_prefix,
            "%scompute" % self._mail_activity_form_prefix,
            "%stype" % self._mail_activity_form_prefix,
        )

    def _mail_activity_form_update(self, html, values):
        """
        Replace the content of all nodes in html with an -id attribute with the
        value from values of that name, return modified html
        """
        _id, _editable, _compute, _type = self._mail_activity_form_attributes()
        for node in html.xpath("//*[@%s]" % (_id)):
            node.text = self._mail_activity_form_format_value(
                values.get(node.attrib[_id]), node.attrib.get(_type),
            )
        return html

    def _mail_activity_form_extract(self, html, compute=False):
        """
        Parse html for nodes marked with {prefix}-editable or -compute
        and return (possibly computed) values
        """
        self.ensure_one()
        _id, _editable, _compute, _type = self._mail_activity_form_attributes()
        vals = {}
        # get static values first, do computations thereafter
        for node in html.xpath("//*[@%s]" % (_id)):
            vals[node.get(_id)] = self._mail_activity_form_extract_value(
                node, vals, compute=False,
            )
        for node in html.xpath("//*[@%s]" % _compute):
            if not node.get(_id):
                # don't compute anonymous nodes here, this happens in
                # _compute
                continue
            vals[node.get(_id)] = self._mail_activity_form_extract_value(
                node, vals, compute=compute,
            )
        return vals

    def _mail_activity_form_extract_value(self, node, values, compute=False):
        """
        Return a value given by node, possibly involving custom evaluation
        """
        _id, _editable, _compute, _type = self._mail_activity_form_attributes()
        expression = node.get(_compute)
        value = None
        if compute and expression:
            value = self._mail_activity_form_eval(expression, values)
        else:
            value = node.text_content().strip()
        value_type = node.get(_type)
        return self._mail_activity_form_parse_value(value, value_type)

    def _mail_activity_form_parse_value(self, value, value_type):
        """
        Cast value to value_type
        """
        if value_type not in ("float", "int", "str", None):
            raise exceptions.UserError(_("Value type %s is invalid",) % value_type)
        return _BUILTINS.get(value_type, _BUILTINS["str"])(value)

    def _mail_activity_form_format_value(self, value, value_type):
        """
        Format a value for representation
        """
        return str(value)

    def _mail_activity_form_eval(self, expression, values):
        """
        Evaluate an expression for this activity
        """
        return tools.safe_eval(
            expression, self._mail_activity_form_eval_context(values,),
        )

    def _mail_activity_form_eval_context(self, values):
        """
        Return the evaluation context for an expression
        """
        res_object = self.env[self.res_model].browse(self.res_id)
        return dict(object=ModelProxy(res_object), activity=ModelProxy(self), **values)

    def _register_hook(self):
        """
        Don't have the HTML cleaner remove our attributes
        """
        mail.safe_attrs |= frozenset(self._mail_activity_form_attributes())
        return super()._register_hook()
