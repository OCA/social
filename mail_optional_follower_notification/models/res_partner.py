# -*- coding: utf-8 -*-
# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def _notify(self, message, force_send=False, user_signature=True):
        if self.env.context.get('force_partners_to_notify'):
            partners_to_notify =\
                self.env.context.get('force_partners_to_notify')
            self = self.filtered(lambda p: p.id in partners_to_notify)
        super(ResPartner, self)._notify(
            message, force_send=False, user_signature=True)
