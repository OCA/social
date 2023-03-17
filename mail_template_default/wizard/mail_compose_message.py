# Copyright 2023 Solvti sp. z o.o. (https://solvti.pl)

from odoo import api, models
from odoo.tools.safe_eval import safe_eval


class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.model
    def default_get(self, fields):
        """Mail Template Rules are sorted base on 4 fields in following hierarchy:
        bool(context_flag) -> bool(company_id) -> bool(field_domain) -> sequence
        The table show hypothetically order:

        +---------+---------+--------+-----+
        | context | company | domain | seq |
        +---------+---------+--------+-----+
        |    x    |    x    |   x    |  1  |
        |    x    |    x    |   x    |  2  |
        |    x    |         |        |  2  |
        |         |    x    |   x    |  1  |
        |         |    x    |        |  1  |
        |         |         |   x    |  2  |
        |         |         |   x    |  3  |
        |         |         |        |  1  |
        """

        res = super(MailComposer, self).default_get(fields)

        res_model = self._context.get("active_model") or self._context.get(
            "default_model"
        )
        res_id = self._context.get("active_id") or self._context.get("default_res_id")
        force_mt = self._context.get("force_mail_template")
        domain = []
        if not res_model or not res_id or force_mt is False:
            return res
        elif force_mt:
            domain += [
                "|",
                ("context_flag", "=", False),
                ("context_flag", "=", force_mt),
            ]
        else:
            # if force_mail_template is None we want to get rid of all rules with context_flag
            domain += [("context_flag", "=", False)]

        rec = self.env[res_model].sudo().browse(res_id)

        if hasattr(rec, "company_id"):
            domain += [
                "|",
                ("company_id", "=", False),
                ("company_id", "=", rec.company_id.id),
            ]

        rule_ids = (
            self.env["mail.template.rule"]
            .sudo()
            .search([("model_id.model", "=", rec._name)] + domain)
        )
        rule_ids = rule_ids.sorted(
            lambda x: (
                not bool(x.context_flag),
                not bool(x.company_id),
                not bool(x.field_domain),
                x.sequence,
            )
        )
        rule_id = self._check_and_pick_rule(rule_ids, rec)
        if rule_id:
            res["template_id"] = rule_id.template_id.id

        return res

    def _check_and_pick_rule(self, rule_ids, obj):
        for rule in rule_ids:
            if rule.field_domain:
                if obj.search_count(
                    [("id", "=", obj.id)] + safe_eval(rule.field_domain)
                ):
                    return rule
            else:
                return rule
