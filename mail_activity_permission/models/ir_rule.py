# Copyright 2023 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models, tools
from odoo.osv.expression import OR
from odoo.tools import config


class IrRule(models.Model):
    _inherit = "ir.rule"

    @api.model
    @tools.conditional(
        "xml" not in config["dev_mode"],
        tools.ormcache(
            "self.env.uid",
            "self.env.su",
            "model_name",
            "mode",
            "tuple(self._compute_domain_context_values())",
        ),
    )
    def _compute_domain(self, model_name, mode="read"):
        """
        Return a domain integrating access to records with a permission-enabling activity type
        or records pointing to other records with a permission-enabling activity type
        """
        rule_domain = super()._compute_domain(model_name, mode=mode)
        if self.env.su or mode not in ("read", "write") or not rule_domain:
            return rule_domain
        activity_domain = self._compute_domain_activity_permission(
            model_name, mode=mode
        )
        return activity_domain and OR([rule_domain, activity_domain]) or rule_domain

    def _compute_domain_activity_permission(self, model_name, mode="read"):
        """Return the domain for accessing records via activity"""
        activity_types = (
            self.env["mail.activity.type"]
            .sudo()
            .search(
                [
                    "|",
                    ("res_model_id.model", "=", model_name),
                    ("field_ids.relation", "=", model_name),
                    ("perm_%s" % mode, "=", True),
                ]
            )
        )
        if not activity_types:
            return []
        activity_domain = (
            [("activity_permission_ids.activity_type_id.perm_%s" % mode, "=", True)]
            if "activity_permission_ids" in self.env[model_name]._fields
            else []
        )
        for field in activity_types.mapped("field_ids"):
            if field.relation != model_name:
                continue
            activity_domain.append(
                (
                    "%s.activity_permission_ids.activity_type_id.perm_%s"
                    % (field.relation_field, mode),
                    "=",
                    True,
                )
            )
        return ["|"] * (len(activity_domain) - 1) + activity_domain
