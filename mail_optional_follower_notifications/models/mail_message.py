# -*- coding: utf-8 -*-
# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, values):
        ctx = self.env.context.copy()
        if not ctx.get('notify_followers') and values.get('partner_ids'):
            force_partners_to_notify = []
            for partner_id in values.get('partner_ids'):
                if isinstance(partner_id, tuple) and\
                        len(partner_id) == 2 and partner_id[0] == 4:
                    force_partners_to_notify.append(partner_id[1])
            ctx['force_partners_to_notify'] = force_partners_to_notify
        return super(MailMessage, self.with_context(ctx)).create(values)
