# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# Copyright 2019 Aleph Objects, Inc.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def _message_auto_subscribe_followers(
            self, updated_values, default_subtype_ids):
        res = super(MailThread, self)._message_auto_subscribe_followers(
            updated_values, default_subtype_ids)
        self_notify_model = self.env['auto.subscribe.notify.own.model'].search(
            [('model_id', '=', self._name), ('active', '=', 'True')], limit=1)
        if self_notify_model:
            res = [(pid, sids, template)
                   if pid != self.env.user.partner_id.id
                   else (pid, sids, 'mail.message_user_assigned')
                   for pid, sids, template in res]
        return res
