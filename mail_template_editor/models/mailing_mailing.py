# Copyright 2025 Kencove - Mohamed Alkobrosli
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MassMailing(models.Model):
    _name = "mailing.mailing"
    _inherit = "mailing.mailing"

    template_id = fields.Many2one(
        "mail.template",
    )

    api.constrains("template_id", "active")

    def _check_template_id_unique(self):
        for rec in self:
            if rec.template_id and rec.active:
                # find other active records with the same template
                duplicates = self.search(
                    [
                        ("id", "!=", rec.id),
                        ("active", "=", True),
                        ("template_id", "=", rec.template_id.id),
                    ],
                    limit=1,
                )
                if duplicates:
                    raise ValidationError(
                        _(
                            "MailTemplate '%s' is already linked to another "
                            "active MassMailing record."
                        )
                        % rec.template_id.name
                    )

    def action_view_template(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Mail Template"),
            "res_model": "mail.template",
            "view_mode": "form",
            "res_id": self.template_id.id,
            "context": {"create": False},
        }
