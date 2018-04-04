# Copyright (C) 2018 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools.safe_eval import safe_eval


class MailFollowers(models.Model):
    _inherit = 'mail.followers'

    @api.model
    def _add_follower_command(self, res_model, res_ids, partner_data,
                              channel_data, force=True):
        domain = self.env[
            'mail.wizard.invite'
        ]._mail_restrict_follower_selection_get_domain()
        partners = self.env['res.partner'].search(
            [('id', 'in', list(partner_data))] +
            safe_eval(domain)
        )
        return super()._add_follower_command(
            res_model, res_ids,
            {p.id: partner_data[p.id] for p in partners},
            channel_data, force=force)
