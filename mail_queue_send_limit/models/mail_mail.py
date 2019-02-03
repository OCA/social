# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from openerp import api, models


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.model
    def process_email_queue(self, ids=None):
        if not ids:
            ids = self.search(
                [('state', '=', 'outgoing')] + self.env.context.get(
                    'filters', []
                ),
                limit=int(self.env['ir.config_parameter'].get_param(
                    'mail_queue_send_limit.limit', '100',
                )),
            ).ids
        return super(MailMail, self).process_email_queue(ids=ids)
