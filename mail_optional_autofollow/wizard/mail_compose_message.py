# -*- coding: utf-8 -*-
# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.model
    def default_get(self, fields_list):
        res = super(MailComposeMessage, self).default_get(fields_list)
        if self.env.context.get('mail_post_autofollow'):
            res['autofollow_recipients'] = True
        return res

    autofollow_recipients = fields.Boolean()

    @api.multi
    def send_mail(self):
        for wizard in self:
            if wizard.autofollow_recipients:
                wizard = wizard.with_context(mail_post_autofollow=True)
            else:
                wizard = wizard.with_context(mail_post_autofollow=False)
            super(MailComposeMessage, wizard).send_mail()
        return {'type': 'ir.actions.act_window_close'}
