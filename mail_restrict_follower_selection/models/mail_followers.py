# Copyright (C) 2018 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools.safe_eval import safe_eval


class MailFollowers(models.Model):
    _inherit = 'mail.followers'

    @api.model
    def _add_default_followers(self, res_model, res_ids, partner_ids,
                               channel_ids=None, customer_ids=None):
        if partner_ids and res_ids:
            domain = self.env[
                'mail.wizard.invite'
            ]._mail_restrict_follower_selection_get_domain()
            partners = self.env['res.partner'].search(
                [('id', 'in', partner_ids)] +
                safe_eval(domain))
            partner_ids = partners.ids
        return super()._add_default_followers(
            res_model, res_ids, partner_ids, channel_ids=channel_ids,
            customer_ids=customer_ids)
