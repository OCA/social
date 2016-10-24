# -*- coding: utf-8 -*-
# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, values):
        ctx = self.env.context.copy()
        if not ctx.get('notify_followers') and values.get('partner_ids'):
            partner_list = self.resolve_2many_commands(
                'partner_ids', values.get('partner_ids'), fields=['id'])
            force_partners_to_notify = [d['id'] for d in partner_list]
            ctx['force_partners_to_notify'] = force_partners_to_notify
        return super(MailMessage, self.with_context(ctx)).create(values)

    @api.multi
    def _notify(self, force_send=False, send_after_commit=True,
                user_signature=True):
        res = super(MailMessage, self)._notify(
            force_send=force_send, send_after_commit=send_after_commit,
            user_signature=user_signature)
        if not self.env.context.get('notify_followers'):
            # Needaction only for recipients
            self.needaction_partner_ids =  [(6, 0, self.partner_ids.ids)]
        return res

