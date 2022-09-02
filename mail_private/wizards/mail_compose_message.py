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
            allow_private = False

            related_res_id = record.res_id
            related_model = record.model
            if related_model and related_res_id:
                related_record = self.env[related_model].browse(related_res_id)
                if hasattr(related_record, 'allow_private'):
                    allow_private = related_record.allow_private

            record.allow_private = allow_private

    def get_mail_values(self, res_ids):
        res = super().get_mail_values(res_ids)
        for r in res:
            res[r]['mail_group_id'] = self.mail_group_id.id
        return res
