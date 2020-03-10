# Copyright 2017 Tecnativa - Pedro M. Baeza
# Copyright 2020 Hibou Corp. - Jared Kipe
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailingLoadFilter(models.TransientModel):
    _name = "mailing.load.filter"
    _description = "Mass Mailing Load Filter"

    filter_id = fields.Many2one(
        comodel_name="ir.filters",
        string="Filter to load",
        required=True,
        domain="[('model_id', '=', 'res.partner'), '|', "
        "('user_id', '=', uid), ('user_id','=',False)]",
        ondelete="cascade",
    )

    def load_filter(self):
        self.ensure_one()
        mass_list = self.env["mailing.list"].browse(self.env.context["active_id"])
        mass_list.sync_domain = self.filter_id.domain
