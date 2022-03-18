from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    show_internal_users_cc = fields.Boolean(
        string="Show Internal Users CC",
        default=True,
    )
    show_followers_message_sent_to = fields.Html(
        string="Text 'Sent to'",
        translate=True,
        default="This message has been sent to",
    )
    show_followers_partner_format = fields.Char(
        string="Partner format",
        default="%(partner_name)s",
        help="Supported parameters:\n"
        "%(partner_name)s = Partner Name\n"
        "%(partner_email)s = Partner Email\n"
        "%(partner_email_domain)s = Partner Email Domain",
    )
    show_followers_message_response_warning = fields.Html(
        string="Text 'Replies'",
        translate=True,
        default="Notice: Replies to this email will be sent to all recipients",
    )
