from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    limit_per_hour = fields.Integer(
        string="Max email sent by hour",
    )

    def _get_current_hour_sent_group(self):
        current_hour_sent_group = self.env["mail.counter"].search_count(
            [
                ("ir_mail_server_id", "=", self.id),
                (
                    "create_date_minute",
                    ">=",
                    fields.Datetime.now() - relativedelta(hour=1),
                ),
            ]
        )
        # IMPROVEMENT search and group on "create_date_minute" to postpone only the
        #  minimum mails possible. Set emails to be postponed only to
        #  (create_date_minute - 60), e.g.
        #  now - 50 minutes: 40 -> send after 10 minutes
        #  now - 30 minutes: 50 -> send after 30 minutes
        #  now - 15 minutes: 10 -> send after 45 minutes
        return current_hour_sent_group

    @api.model
    def send_email(
        self,
        message,
        mail_server_id=None,
        smtp_server=None,
        smtp_port=None,
        smtp_user=None,
        smtp_password=None,
        smtp_encryption=None,
        smtp_ssl_certificate=None,
        smtp_ssl_private_key=None,
        smtp_debug=False,
        smtp_session=None,
    ):
        mail_counter_obj = self.env["mail.counter"]
        # scheduled_date is already set in send() method
        message_id = super().send_email(
            message=message,
            mail_server_id=mail_server_id,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_encryption=smtp_encryption,
            smtp_ssl_certificate=smtp_ssl_certificate,
            smtp_ssl_private_key=smtp_ssl_private_key,
            smtp_debug=smtp_debug,
            smtp_session=smtp_session,
        )
        if not mail_server_id:
            mail_server, smtp_from = self.sudo()._find_mail_server(message["From"])
            mail_server_id = mail_server.id
        mail_counter_obj.create(
            {
                "mail_sent_message_id": message_id,
                "ir_mail_server_id": mail_server_id,
            }
        )
        return message_id
