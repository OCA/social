#  Copyright 2023 Simone Rubino - TAKOBI
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MassMailing (models.Model):
    _inherit = 'mail.mass_mailing'

    def get_remaining_recipients(self):
        recipients_res_ids = super(MassMailing, self).get_remaining_recipients()
        batch_size = self.env['ir.config_parameter'] \
            .sudo() \
            .get_param(
                'mass_mailing_batch.size',
                default=None,
            )
        if batch_size is not None:
            batch_size = int(batch_size)
            recipients_res_ids = recipients_res_ids[:batch_size]

        return recipients_res_ids

    def send_mail(self):
        result = super(MassMailing, self).send_mail()
        for mass_mailing in self:
            if len(mass_mailing.get_remaining_recipients()) > 0:
                mass_mailing.state = 'sending'
        return result
