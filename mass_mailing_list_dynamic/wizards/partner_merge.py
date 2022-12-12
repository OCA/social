# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = "base.partner.merge.automatic.wizard"

    def _merge(self, partner_ids, dst_partner=None, extra_checks=True):
        return super(
            BasePartnerMergeAutomaticWizard, self.with_context(syncing=True)
        )._merge(
            partner_ids=partner_ids,
            dst_partner=dst_partner,
            extra_checks=extra_checks,
        )
