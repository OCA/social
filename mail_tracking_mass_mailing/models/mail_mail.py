# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2017 Vicent Cubells - <vicent.cubells@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class MailMail(models.Model):
    _inherit = "mail.mail"

    @api.model
    def _tracking_email_prepare(self, partner, email):
        res = super(MailMail, self)._tracking_email_prepare(partner, email)
        res["mail_id_int"] = self.id
        res["mass_mailing_id"] = self.mailing_id.id
        res["mail_stats_id"] = (
            self.mailing_trace_ids[:1].id if self.mailing_trace_ids else False
        )
        return res

    @api.model
    def _get_tracking_url(self):
        # Invalid this tracking image, we have other to do the same
        return False

    def _postprocess_sent_message(
        self, success_pids, failure_reason=False, failure_type=None
    ):
        """Set mailing traces in error according to mail tracking state

        If an exception is caught by ir.mail_server.send_email in mail_tracking module,
        the mail.tracking.email record will appear in error but the related mailing
        trace would still appear as sent because this method is called without any
        failure_type in mail.mail._send in the mail module (as Exception is not raised
        after being caught in mail_tracking module).

        Since this method not only sets the mailing.trace state in mass_mailing module
        but can also delete the mail.mail records in mail module, we need to ensure
        the mailing.trace is written accordingly to the tracking here, and avoid having
        the mass_mailing module set a 'sent' status if we had an exception, hence
        the usage of a context key to ignore possible writes.
        """
        processed_ids = []
        for mail in self:
            mail_tracking = mail.mailing_trace_ids.mail_tracking_id
            if mail.mailing_id and mail_tracking.state == "error":
                mail_failure_type = (
                    "RECIPIENT"
                    if mail_tracking.error_type == "no_recipient"
                    else "SMTP"
                )
                mail.mailing_trace_ids.write(
                    {
                        "exception": fields.Datetime.now(),
                        "failure_type": mail_failure_type,
                    }
                )
                processed_ids.extend(mail.mailing_trace_ids.ids)
        return super(
            MailMail,
            self.with_context(_ignore_write_trace_postprocess_ids=processed_ids),
        )._postprocess_sent_message(
            success_pids, failure_reason=failure_reason, failure_type=failure_type
        )
