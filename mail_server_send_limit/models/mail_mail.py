from dateutil.relativedelta import relativedelta

from odoo import fields, models


class MailMail(models.Model):
    _inherit = "mail.mail"

    def send(self, auto_commit=False, raise_exception=False):
        for (
            mail_server_id,
            _smtp_from,
            _batch_ids,
        ) in self._split_by_mail_configuration():
            mail_server = self.env["ir.mail_server"].browse(mail_server_id)
            limit_per_hour = mail_server.limit_per_hour
            if not limit_per_hour:
                continue
            current_hour_sent_group = mail_server._get_current_hour_sent_group()
            if current_hour_sent_group or len(self.ids) >= limit_per_hour:
                tobe_postponed_emails = self
                # we postpone some mail only in case they are less than the limit
                if current_hour_sent_group < limit_per_hour:
                    tobe_postponed_emails = self[
                        limit_per_hour - current_hour_sent_group :
                    ]
                if len(self.ids) >= limit_per_hour > current_hour_sent_group:
                    tobe_postponed_emails = self[
                        limit_per_hour - current_hour_sent_group :
                    ]
                self -= tobe_postponed_emails
                # set scheduled_date for email exceeding the hourly limit
                current_i = 0
                for i in range(
                    limit_per_hour,
                    len(tobe_postponed_emails) + limit_per_hour - 1,
                    limit_per_hour,
                ):
                    tobe_postponed_emails[current_i:i].write(
                        {
                            "scheduled_date": fields.Datetime.now()
                            + relativedelta(hours=int(i / limit_per_hour))
                        }
                    )
                    current_i = i

        return super().send(auto_commit=auto_commit, raise_exception=raise_exception)
