# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailMessageImportConfig(models.Model):
    """Settings of the module for one company.

    They are kept apart from the general settings so the managers of the
    application can change them without being administrators. The modules that
    process the conversations add their own settings here.

    The user that acts for the module depends on the deployment: a module may
    give it through ``_agent_user``.
    """

    _name = "mail.message.import.config"
    _description = "Message Import Settings"
    _rec_name = "company_id"
    _check_company_auto = True

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    inactivity_minutes = fields.Integer(
        default=3,
        required=True,
        help="Minutes without new messages of a sender before its messages are "
        "processed together.",
    )
    max_attempts = fields.Integer(
        string="Maximum attempts",
        default=5,
        required=True,
        help="Attempts to process a conversation before it is left in error.",
    )

    _sql_constraints = [
        ("company_uniq", "unique(company_id)", "The company already has settings."),
    ]

    @api.constrains("inactivity_minutes", "max_attempts")
    def _check_values(self):
        for config in self:
            if not 1 <= config.inactivity_minutes <= 1440:
                raise ValidationError(
                    _("The inactivity must last between 1 and 1440 minutes.")
                )
            if config.max_attempts < 1:
                raise ValidationError(_("The limits must be positive."))

    @api.model
    def _agent_user(self, company=None):
        """The user that acts and signs for the module when nobody triggered
        the action, if it works in ``company``; otherwise OdooBot does."""
        return self.env["res.users"]

    @api.model
    def _get_for_company(self, company):
        config = self.sudo().search([("company_id", "=", company.id)], limit=1)
        return config or self.sudo().create({"company_id": company.id})

    @api.model
    def action_open_company_config(self):
        config = self._get_for_company(self.env.company)
        return {
            "type": "ir.actions.act_window",
            "name": _("Settings"),
            "res_model": self._name,
            "res_id": config.id,
            "view_mode": "form",
            "target": "current",
        }
