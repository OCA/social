# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools

from odoo import fields, models


class SocialPost(models.Model):
    _inherit = "social.post"

    campaign_id = fields.Many2one("utm.campaign", domain=[("account_id", "!=", False)])

    def _default_account_ids(self):
        res = super()._default_account_ids()
        account_ids = (
            self.env["social.account"]
            .with_company(self.env.company)
            .search([("media_type", "=", "linkedin")])
        )
        if account_ids:
            return list(itertools.chain(account_ids.ids, res))
        return res
