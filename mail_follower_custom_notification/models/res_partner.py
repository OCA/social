# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def _notify_by_email(
        self, message, force_send=False, send_after_commit=True,
        user_signature=True,
    ):
        """remove partners from `self` who requested not to be mailed,
        add the ones who did the opposite"""
        domain = [
            ('res_model', '=', message.model),
            ('res_id', '=', message.res_id),
        ]
        self |= self.env['mail.followers'].search(
            domain + [('force_mail_subtype_ids', '=', message.subtype_id.id)]
        ).mapped('partner_id')
        self -= self.env['mail.followers'].search(
            domain + [('force_nomail_subtype_ids', '=', message.subtype_id.id)]
        ).mapped('partner_id')
        return super(ResPartner, self)._notify_by_email(
            message, force_send=force_send,
            send_after_commit=send_after_commit, user_signature=user_signature,
        )
