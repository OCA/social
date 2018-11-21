# -*- coding: utf-8 -*-
# Copyright 2016 Odoo SA <https://www.odoo.com>
# Copyright 2018 Therp BV <http://therp.nl>
# Copyright 2018 Eficent <http://www.eficent.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
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
