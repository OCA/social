# Copyright (C) 2015 Therp BV <http://therp.nl>
# Copyright (C) 2017 Komit <http://www.komit-consulting.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from lxml import etree

from odoo import api, models
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class MailWizardInvite(models.TransientModel):
    _inherit = "mail.wizard.invite"

    @api.model
    def _mail_restrict_follower_selection_get_domain(self, res_model=None):
        if not res_model:
            res_model = self.env.context.get("default_res_model")
        parameter_name = "mail_restrict_follower_selection.domain"
        parameter_domain = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                f"{parameter_name}.{res_model}",
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(parameter_name, default="[]"),
            )
        )
        domain = expression.AND(
            [safe_eval(parameter_domain), self._fields["partner_ids"].domain]
        )
        return domain

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        arch = etree.fromstring(result["arch"])
        for field in arch.xpath('//field[@name="partner_ids"]'):
            field.attrib["domain"] = str(
                self._mail_restrict_follower_selection_get_domain()
            )
        result["arch"] = etree.tostring(arch)
        return result
