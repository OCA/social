# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailComposeMessage(models.TransientModel):

    _inherit = 'mail.compose.message'

    allow_private = fields.Boolean(
        compute='_compute_allow_private',
        compute_sudo=True,
    )

    @api.depends('model', 'res_id')
    def _compute_allow_private(self):
        for record in self:
            record.allow_private = record.model and record.res_id and self.env[
                record.model
            ].browse(record.res_id).allow_private

    def get_mail_values(self, res_ids):
        res = super().get_mail_values(res_ids)
        for r in res:
            res[r]['mail_group_id'] = self.mail_group_id.id
        return res
