# -*- coding: utf-8 -*-
# (c) 2015 Serv. Tecnol. Avanzados - Pedro M. Baeza
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, api


class MailWizardInvite(models.TransientModel):
    _inherit = 'mail.wizard.invite'

    @api.multi
    def add_followers(self):
        obj = self.with_context(allow_follower_subscription=True)
        return super(MailWizardInvite, obj).add_followers()
