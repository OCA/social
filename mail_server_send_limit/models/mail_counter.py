from odoo import fields, models


class MailCounter(models.Model):
    _name = "mail.counter"
    _description = "Mail Counter"

    mail_sent_message_id = fields.Char(string="Mail sent Message-Id")
    ir_mail_server_id = fields.Many2one(
        comodel_name="ir.mail_server",
        string="Mail server",
    )
    create_date_minute = fields.Datetime(
        string="Creation minute",
        help="Datetime without seconds and microseconds",
        default=fields.Datetime.now().replace(microsecond=0, second=0),
    )
