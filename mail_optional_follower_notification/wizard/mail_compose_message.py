# -*- coding: utf-8 -*-
# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    notify_followers = fields.Boolean(default=True)

    @api.multi
    def send_mail(self):
        for wizard in self:
            wizard = wizard.with_context(
                notify_followers=wizard.notify_followers)
            super(MailComposeMessage, wizard).send_mail()
        return {'type': 'ir.actions.act_window_close'}
