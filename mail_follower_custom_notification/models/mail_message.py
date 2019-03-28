# -*- coding: utf-8 -*-
# Copyright 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.multi
    def _notify(
        self, force_send=False, send_after_commit=True, user_signature=True,
    ):
        """notify author if she's a follower and turned on force_own"""
        self.ensure_one()
        if self.subtype_id and self.model and self.res_id and self.env[
                'mail.followers'
        ].search([
                ('res_model', '=', self.model),
                ('res_id', '=', self.res_id),
                ('partner_id', '=', self.author_id.id),
                ('force_own_subtype_ids', '=', self.subtype_id.id),
        ]):
            self = self.with_context(mail_notify_author=True)
        return super(MailMessage, self)._notify(
            force_send=force_send, send_after_commit=send_after_commit,
            user_signature=user_signature,
        )
