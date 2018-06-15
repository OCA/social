# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    @api.multi
    def action_create_calendar_event(self):
        action = super(MailActivity, self).action_create_calendar_event()
        res_model = self.env.context.get('default_res_model', False)
        if res_model and res_model == 'crm.lead':
            action['context']['default_opportunity_id'] = \
                self.env.context.get('default_res_id')
        return action
