# Copyright 2020 ABF OSIELL <http://osiell.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        return super(AccountInvoice, self.with_context(
            mail_post_autofollow_override=self.env.context.get(
                'mail_post_autofollow', True))).message_post(**kwargs)
