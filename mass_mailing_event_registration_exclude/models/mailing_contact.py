# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2020 Tecnativa - Alexandre D. Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from .mailing import event_filtered_ids


class MassMailingContact(models.Model):
    _inherit = "mailing.contact"

    @api.model
    def search_count(self, domain):
        res = super().search_count(domain)
        mass_mailing_id = self.env.context.get("exclude_mass_mailing", False)
        if mass_mailing_id:
            res_ids = event_filtered_ids(self, mass_mailing_id, domain, field="email")
            res = len(res_ids) if res_ids else 0
        return res
