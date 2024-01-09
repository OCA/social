# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailTemplate(models.Model):

    _inherit = "mail.template"

    # Fake field for auto-completing placeholder
    placeholder_id = fields.Many2one(
        comodel_name="email.template.placeholder",
        string="Placeholder",
    )
    placeholder_value = fields.Char()

    @api.onchange("placeholder_id")
    def _onchange_placeholder_id(self):
        for tmpl in self:
            if tmpl.placeholder_id:
                tmpl.placeholder_value = tmpl.placeholder_id.placeholder
