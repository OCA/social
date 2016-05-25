# -*- coding: utf-8 -*-
# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api


class MailNotification(models.Model):
    _inherit = 'mail.notification'

    @api.model
    def _notify(self, message_id, partners_to_notify=None,
                force_send=False, user_signature=True):
        if self.env.context.get('force_partners_to_notify'):
            partners_to_notify =\
                self.env.context.get('force_partners_to_notify')
        super(MailNotification, self)._notify(
            message_id, partners_to_notify=partners_to_notify,
            force_send=force_send, user_signature=user_signature)
