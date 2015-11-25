# -*- coding: utf-8 -*-
# © 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.multi
    def _notify(self, force_send=False, user_signature=True):
        """notify author if she's a follower and turned on force_own"""
        self.ensure_one()
        if self.subtype_id and self.model and self.res_id:
            author_follower = self.env['mail.followers'].search([
                ('res_model', '=', self.model),
                ('res_id', '=', self.res_id),
                ('partner_id', '=', self.author_id.id),
                ('force_own_subtype_ids', '=', self.subtype_id.id),
            ])
            self.env['mail.notification']._notify(
                self.id, partners_to_notify=author_follower.partner_id.ids,
                force_send=force_send, user_signature=user_signature)
        return super(MailMessage, self)._notify(
            self.id, force_send=force_send, user_signature=user_signature)
