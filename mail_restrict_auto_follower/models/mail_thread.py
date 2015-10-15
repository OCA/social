# -*- coding: utf-8 -*-
# (c) 2015 Serv. Tecnol. Avanzados - Pedro M. Baeza
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, api
from openerp.tools.safe_eval import safe_eval


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def _mail_restrict_follower_get_domain(self):
        parameter_name = 'mail_restrict_auto_follower.domain'
        return self.env['ir.config_parameter'].get_param(
            '%s.%s' % (parameter_name, self._name),
            default=self.env['ir.config_parameter'].get_param(
                parameter_name, default='[]'))

    @api.multi
    def message_subscribe(self, partner_ids, subtype_ids=None):
        if self.env.context.get('allow_follower_subscription'):
            new_partner_ids = partner_ids
        else:
            partner_model = self.env['res.partner']
            domain = self._mail_restrict_follower_get_domain()
            valid_partners = partner_model.search(safe_eval(domain))
            valid_partner_ids = set(valid_partners.ids)
            new_partner_ids = list(valid_partner_ids & set(partner_ids))
        return super(MailThread, self).message_subscribe(
            new_partner_ids, subtype_ids=subtype_ids)
