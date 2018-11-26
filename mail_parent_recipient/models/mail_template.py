# -*- coding: utf-8 -*-
# Copyright 2018 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models, api


class MailTemplate(models.Model):

    _inherit = 'mail.template'

    @api.multi
    def generate_recipients(self, results, res_ids):
        """
        Modify the code that set the default recipient in an email to the first
        partner having an email set following the parents tree.
        If no parent with an email is found,
        it reverts to the popup asking to set an email for the current partner
        """
        results = super(MailTemplate, self).generate_recipients(
            results,
            res_ids
        )
        for res_id, values in results.iteritems():
            partner_ids = values.get('partner_ids', [])
            partners_with_emails = []
            for partner in self.env['res.partner'].sudo().browse(partner_ids):
                current = partner
                while current:
                    if current.email:
                        break
                    current = current.parent_id
                partners_with_emails.append(current.id or partner.id)

            results[res_id]['partner_ids'] = partners_with_emails
        return results
