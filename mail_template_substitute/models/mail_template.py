# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools import pycompat
from odoo.tools.safe_eval import safe_eval


class MailTemplate(models.Model):

    _inherit = "mail.template"

    mail_template_substitution_rule_ids = fields.One2many(
        comodel_name="mail.template.substitution.rule",
        inverse_name="mail_template_id",
        string="Substitution Rules",
    )

    @api.multi
    def _get_substitution_template(self, model_id, active_ids):
        self.ensure_one()
        if isinstance(active_ids, pycompat.integer_types):
            active_ids = [active_ids]
        model = self.env[model_id.model]
        for (
            substitution_template_rule
        ) in self.mail_template_substitution_rule_ids:
            domain = safe_eval(substitution_template_rule.domain)
            domain.append(("id", "in", active_ids))
            if set(model.search(domain).ids) == set(active_ids):
                return substitution_template_rule.substitution_mail_template_id
        return False

    @api.multi
    def get_email_template(self, res_ids):
        substitution_template = self._get_substitution_template(
            self.model_id, res_ids
        )
        if substitution_template:
            return substitution_template.get_email_template(res_ids)
        return super().get_email_template(res_ids)
