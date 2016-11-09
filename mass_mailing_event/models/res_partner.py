# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, api
from .mail_mass_mailing import event_filtered_ids


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def search_count(self, domain):
        res = super(ResPartner, self).search_count(domain)
        mass_mailing_id = self.env.context.get('exclude_mass_mailing', False)
        if mass_mailing_id:
            res_ids = event_filtered_ids(
                self, mass_mailing_id, domain, field='email')
            return len(res_ids) if res_ids else 0
        return res
