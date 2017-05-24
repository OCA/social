# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __openerp__.py
#
##############################################################################

from openerp import models, api, tools


class TestMassMailing(models.TransientModel):
    _inherit = 'mail.mass_mailing.test'

    @api.multi
    def send_mail_test(self):
        """ Send with Sendgrid if needed.
        """
        self.ensure_one()
        mailing = self.mass_mailing_id
        template = mailing.email_template_id
        if template:
            # Send with SendGrid (and use E-mail Template)
            test_emails = tools.email_split(self.email_to)
            emails = self.env['mail.mail']
            for test_mail in test_emails:
                emails += emails.create({
                    'email_from': mailing.email_from,
                    'reply_to': mailing.reply_to,
                    'email_to': test_mail,
                    'subject': mailing.name,
                    'body_html': mailing.body_html,
                    'sendgrid_template_id':
                        template.sendgrid_localized_template.id,
                    'notification': True,
                    'mailing_id': mailing.id,
                    'attachment_ids': [(4, attachment.id) for attachment in
                                       mailing.attachment_ids],
                })
            emails.send_sendgrid()
            mailing.write({
                'state': 'test',
            })
        else:
            super(TestMassMailing, self).send_mail_test()

        return True
