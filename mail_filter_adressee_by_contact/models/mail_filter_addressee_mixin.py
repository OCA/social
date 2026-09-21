# Copyright (C) 2026 Akretion (<http://www.akretion.com>).
# @author Kévin Roche <kevin.roche@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.osv import expression


class MailFilterAddresseeMixin(models.AbstractModel):
    _name = "mail.filter.addressee.mixin"
    _description = "Mixin to filter mail addressees by contact type"

    # Name of the Many2many partner field targeted by the domain.
    # Override in concrete models when the field is not 'partner_ids'
    # (e.g. 'mail_partner_ids' on account.move.send.wizard).
    _partner_ids_field = "partner_ids"

    apply_filter = fields.Selection(
        [
            ("contacts", "Contacts"),
            ("users", "Users"),
            ("all", "All"),
        ],
        string="Filtering relevant adressees",
        default="contacts",
        required=True,
    )

    partner_ids_domain = fields.Binary(
        compute="_compute_partner_ids_domain",
    )

    @api.depends("apply_filter")
    def _compute_partner_ids_domain(self):
        for record in self:
            domain = [("email", "!=", False)]
            model = self._context.get("active_model")

            if model and record.apply_filter == "contacts":
                method_name = f"_get_domain_for_{model.replace('.', '_')}"
                if hasattr(self, method_name):
                    records = self.env[model].browse(self._context.get("active_ids"))
                    partners = getattr(self, method_name)(records)
                    domain = expression.AND([domain, partners])

            if record.apply_filter == "users":
                domain = expression.AND([domain, [("user_ids", "!=", False)]])
            record.partner_ids_domain = domain

    def _get_domain_for_account_move(self, records):
        return [
            "|",
            ("id", "child_of", records.partner_id.ids),
            ("id", "in", records.message_partner_ids.ids),
        ]
