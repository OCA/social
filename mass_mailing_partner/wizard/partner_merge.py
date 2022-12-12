# Copyright 2020 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = "base.partner.merge.automatic.wizard"

    def _merge(self, partner_ids, dst_partner=None, extra_checks=True):
        if dst_partner:
            contacts = (
                self.env["mailing.contact"]
                .sudo()
                .search([("partner_id", "in", partner_ids)])
            )
            if contacts:
                contacts = contacts.sorted(
                    lambda x: 1 if x.partner_id == dst_partner else 0
                )
                list_ids = contacts.mapped("list_ids").ids
                contacts[1:].unlink()
                contacts[0].partner_id = dst_partner
                contacts[0].list_ids = [(4, x) for x in list_ids]
        return super()._merge(
            partner_ids, dst_partner=dst_partner, extra_checks=extra_checks
        )
