# -*- coding: utf-8 -*-
# © 2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.tests.common import TransactionCase


class TestMailNotificationEmailTemplate(TransactionCase):
    def test_mail_notification_email_template(self):
        # demo data install a template for discussions, so we simply post
        # something somewhere. We know the demo user is subscribed on the
        # whole company group
        demo_partner = self.env.ref('base.partner_demo')
        demo_partner.write({'notify_email': 'always'})
        demo_partner_mails = self.env['mail.mail'].search([
            ('recipient_ids', '=', demo_partner.id),
        ])
        self.env.ref('mail.group_all_employees').message_post(
            body='hello world', type='comment', subtype='mail.mt_comment')
        notification = self.env['mail.mail'].search([
            ('recipient_ids', '=', demo_partner.id),
        ]) - demo_partner_mails
        self.assertTrue(notification)
        # check that our template was used
        self.assertTrue('<h2>Dear ' in notification.body)
