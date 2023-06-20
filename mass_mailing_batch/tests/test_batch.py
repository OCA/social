#  Copyright 2023 Simone Rubino - TAKOBI
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from mock import mock

from odoo import tests


class TestBatch (tests.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestBatch, cls).setUpClass()

        cls.mass_mailing_cron = cls.env.ref('mass_mailing.ir_cron_mass_mailing_queue')

        partner_model = cls.env['res.partner']
        cls.recipients = partner_model.browse()
        for recipient_index in range(20):
            recipient = partner_model.create({
                'name': str(recipient_index),
            })
            cls.recipients |= recipient

        cls.mass_mailing = cls.env['mail.mass_mailing'].create({
            'name': "Test Mass Mailing Batch",
            'mailing_model': 'res.partner',
            'reply_to_mode': 'email',
        })
        cls.mass_mailing.put_in_queue()

        # Mock mail sending
        # because during mass mailing autocommit is set to True,
        # and it invalidates the test's SAVEPOINT
        cls.patcher = mock.patch('odoo.addons.mail.models.mail_mail.MailMail.send')
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()
        super(TestBatch, cls).tearDownClass()

    def test_no_batch(self):
        """Without batch, all the emails are sent in one CRON iteration."""
        mass_mailing = self.mass_mailing
        recipients_count = len(mass_mailing.get_remaining_recipients())
        # pre-condition
        self.assertTrue(recipients_count)
        self.assertFalse(
            self.env['ir.config_parameter'].get_param(
                'mass_mailing_batch.size',
                default=None,
            ),
        )

        self.mass_mailing_cron.method_direct_trigger()

        recipients_count = len(mass_mailing.get_remaining_recipients())
        self.assertFalse(recipients_count)
        self.assertEqual(mass_mailing.state, 'done')

    def test_batch(self):
        """`batch` emails are sent in each CRON iteration."""
        batch_size = 10
        self.env['ir.config_parameter'].set_param(
            'mass_mailing_batch.size',
            str(batch_size),
        )
        mass_mailing = self.mass_mailing
        recipients_count = len(mass_mailing.get_remaining_recipients())
        self.assertTrue(recipients_count)

        # CRON iteration 1
        self.mass_mailing_cron.method_direct_trigger()

        # Assert 1: Mass mailing is still 'sending'
        recipients_count = len(mass_mailing.get_remaining_recipients())
        self.assertTrue(recipients_count)
        self.assertEqual(mass_mailing.state, 'sending')
        # `batch` emails have been sent
        # (we have to disable the batch mechanism)
        all_recipients = len(mass_mailing.get_recipients())
        self.env['ir.config_parameter'].set_param(
            'mass_mailing_batch.size',
            None,
        )
        recipients_count = len(mass_mailing.get_remaining_recipients())
        self.assertEqual(recipients_count, all_recipients - batch_size)

        # Restore the batch mechanism to send all the remaining emails
        self.env['ir.config_parameter'].set_param(
            'mass_mailing_batch.size',
            str(recipients_count),
        )

        # CRON iteration 2
        self.mass_mailing_cron.method_direct_trigger()

        # Assert 2: Now all the emails have been sent
        recipients_count = len(mass_mailing.get_remaining_recipients())
        self.assertFalse(recipients_count)
        self.assertEqual(mass_mailing.state, 'done')
