# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ResPartner(models.Model):

    _inherit = 'res.partner'

    @api.multi
    def _notify(self, message, force_send=False, send_after_commit=True,
                user_signature=True):
        if not message.mail_group_id:
            return super(ResPartner, self)._notify(
                message, force_send=force_send,
                send_after_commit=send_after_commit,
                user_signature=user_signature
            )
        accepted_users = message.mail_group_id.mapped(
            'group_ids.users')
        partners = self.browse()
        for partner in self:
            if partner.user_ids in accepted_users:
                partners |= partner
        return super(ResPartner, partners)._notify(
            message, force_send=force_send,
            send_after_commit=send_after_commit, user_signature=user_signature
        )

    @api.multi
    def _notify_by_chat(self, message):
        if not message.mail_group_id:
            return super()._notify_by_chat(message)
        accepted_users = message.mail_group_id.mapped(
            'group_ids.users')
        partners = self.browse()
        for partner in self:
            if partner.user_ids in accepted_users:
                partners |= partner
            elif partner.user_ids:
                message.sudo(partner.user_ids[0]).set_message_done()
        return super(ResPartner, partners)._notify_by_chat(message)
