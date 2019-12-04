# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    notify_followers = fields.Boolean(default=True)

    @api.multi
    def send_mail(self, auto_commit=False):
        ctx = self.env.context.copy()
        for wizard in self:
            ctx['notify_followers'] = wizard.notify_followers
            wizard = wizard.with_context(ctx)
            super(MailComposeMessage, wizard).send_mail(
                auto_commit=auto_commit)
        return {'type': 'ir.actions.act_window_close'}
