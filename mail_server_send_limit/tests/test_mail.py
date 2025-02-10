from odoo import fields
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger
from odoo.tools.date_utils import relativedelta

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged("-at_install", "post_install")
class TestMassMailing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.IrMailServer = cls.env["ir.mail_server"]
        cls.server = cls.IrMailServer.create(
            {
                "name": "server mail",
                "smtp_host": "test1.smtp",
            }
        )
        cls.list = cls.env["mailing.list"].create({"name": "Test mail limit"})
        cls.list.name = f"{cls.list.name} #{cls.list.id}"
        contacts = cls.env["mailing.contact"].browse()
        for i in range(0, 312):
            contacts |= cls.env["mailing.contact"].create(
                {
                    "list_ids": [(6, 0, cls.list.ids)],
                    "name": f"Test contact {i}",
                    "email": f"contact_{i}@example.com",
                }
            )
        cls.mailing = cls.env["mailing.mailing"].create(
            {
                "subject": "Test subject",
                "email_from": "from@example.com",
                "mailing_model_id": cls.env.ref(
                    "mass_mailing.model_mailing_contact"
                ).id,
                "mailing_domain": [("list_ids", "in", cls.list.id)],
                "contact_list_ids": [(6, False, [cls.list.id])],
                "body_html": "<p>Test email body</p>",
                "reply_to_mode": "new",
            }
        )

    @mute_logger("odoo.addons.mail.models.mail_mail", "odoo.models.unlink")
    def test_email_send_without_limit(self):
        previous_mail_sent = self.env["mail.counter"].search_count([])
        self.mailing.action_send_mail()
        for stat in self.mailing.mailing_trace_ids:
            if stat.mail_mail_id:
                stat.mail_mail_id.send()
        mail_sent = self.env["mail.counter"].search_count([])
        self.assertEqual(
            len(self.mailing.contact_list_ids.contact_ids),
            mail_sent - previous_mail_sent,
        )

    @mute_logger("odoo.addons.mail.models.mail_mail", "odoo.models.unlink")
    def test_email_send_with_limit(self):
        previous_mail_sent = self.env["mail.counter"].search_count([])
        self.server.limit_per_hour = 100
        self.mailing.action_send_mail()
        for stat in self.mailing.mailing_trace_ids:
            if stat.mail_mail_id:
                stat.mail_mail_id.send()
        mail_sent = self.env["mail.counter"].search_count([])
        self.assertEqual(100, mail_sent - previous_mail_sent)
        first_postponed_mails = self.env["mail.mail"].search(
            [("scheduled_date", "<=", fields.Datetime.now() + relativedelta(hours=1))]
        )
        self.assertEqual(
            len(first_postponed_mails),
            100,
        )
        last_postponed_mails = self.env["mail.mail"].search(
            [("scheduled_date", ">", fields.Datetime.now() + relativedelta(hours=1))]
        )
        self.assertEqual(
            len(last_postponed_mails),
            len(self.mailing.contact_list_ids.contact_ids) - 200,
        )
