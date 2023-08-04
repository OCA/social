# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailComposeMessage(models.TransientModel):

    _inherit = "mail.compose.message"

    @api.model
    def _get_substitution_template(self, composition_mode, template, res_ids):
        if template:
            if composition_mode == "mass_mail" and self.env.context.get("active_ids"):
                res_ids = self.env.context.get("active_ids")
            res_ids_to_templates = template._classify_per_lang(res_ids)
            if len(res_ids_to_templates):
                _lang, (template, _res_ids) = list(res_ids_to_templates.items())[0]
                return template
        return False

    @api.model
    def default_get(self, fields):
        result = super(MailComposeMessage, self).default_get(fields)
        substitution_template = self._get_substitution_template(
            result.get("composition_mode"),
            self.env["mail.template"].browse(result.get("template_id")),
            [result.get("res_id")],
        )
        if substitution_template:
            result["template_id"] = substitution_template.id
        return result

    @api.onchange("template_id")
    def onchange_template_id_wrapper(self):
        substitution_template = self._get_substitution_template(
            self.composition_mode, self.template_id, [self.res_id]
        )
        if substitution_template:
            self.template_id = substitution_template
        return super().onchange_template_id_wrapper()
