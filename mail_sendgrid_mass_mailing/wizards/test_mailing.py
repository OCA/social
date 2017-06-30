# -*- coding: utf-8 -*-
# Copyright 2016-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, tools


class TestMassMailing(models.TransientModel):
    _inherit = 'mail.mass_mailing.test'

    @api.multi
    def send_mail_test(self):
        """ Send with Sendgrid if needed.
        """
        self.ensure_one()
        mailing = self.mass_mailing_id
        template = mailing.email_template_id.with_context(
            lang=mailing.lang.code or self.env.context['lang'])
        if template:
            # Send with SendGrid (and use E-mail Template)
            sendgrid_template = template.sendgrid_localized_template
            res_id = self.env.user.partner_id.id
            body = template.render_template(
                mailing.body_html, template.model, [res_id],
                post_process=True)[res_id]
            test_emails = tools.email_split(self.email_to)
            emails = self.env['mail.mail']
            for test_mail in test_emails:
                email_vals = {
                    'email_from': mailing.email_from,
                    'reply_to': mailing.reply_to,
                    'email_to': test_mail,
                    'subject': mailing.name,
                    'body_html': body,
                    'sendgrid_template_id': sendgrid_template.id,
                    'substitution_ids': template.render_substitutions(
                        res_id)[res_id],
                    'notification': True,
                    'mailing_id': mailing.id,
                    'attachment_ids': [(4, attachment.id) for attachment in
                                       mailing.attachment_ids],
                }
                emails += emails.create(email_vals)
            emails.send_sendgrid()
        else:
            super(TestMassMailing, self).send_mail_test()

        return True
