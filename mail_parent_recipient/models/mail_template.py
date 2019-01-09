# -*- coding: utf-8 -*-
# Copyright 2018 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models, api
from odoo.tools import config


class MailTemplate(models.Model):

    _inherit = 'mail.template'

    @api.multi
    def generate_recipients(self, results, res_ids):
        """Use partner's parent email as recipient.

        Walk up the hierarchy of recipient partners via `parent_id`
        and pick the 1st one having an email.
        """
        results = super(MailTemplate, self).generate_recipients(
            results,
            res_ids
        )
        test_condition = (
            config['test_enable'] and not self.env.context.get(
                'test_parent_mail_recipient'
            )
        )
        if not test_condition and not self.env.context.get(
            'no_parent_mail_recipient'
        ):
            for res_id, values in results.iteritems():
                partner_ids = values.get('partner_ids', [])
                partners_with_emails = []
                partners = self.env['res.partner'].sudo().browse(partner_ids)
                for partner in partners:
                    current = partner
                    while current:
                        if current.email:
                            break
                        current = current.parent_id
                    partners_with_emails.append(current.id or partner.id)

                results[res_id]['partner_ids'] = partners_with_emails
        return results
