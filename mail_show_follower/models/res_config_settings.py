from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    show_internal_users_cc = fields.Boolean(
        related="company_id.show_internal_users_cc",
        readonly=False,
    )
    show_followers_message_sent_to = fields.Html(
        related="company_id.show_followers_message_sent_to",
        readonly=False,
    )
    show_followers_partner_format = fields.Char(
        related="company_id.show_followers_partner_format",
        readonly=False,
        help="Supported parameters:\n"
        "%(partner_name)s = Partner Name\n"
        "%(partner_email)s = Partner Email\n"
        "%(partner_email_domain)s = Partner Email Domain",
    )
    show_followers_message_response_warning = fields.Html(
        related="company_id.show_followers_message_response_warning",
        readonly=False,
    )
    show_followers_message_preview = fields.Html(
        string="Message preview",
        readonly=True,
        store=False,
    )

    @api.onchange(
        "show_followers_message_sent_to",
        "show_followers_partner_format",
        "show_followers_message_response_warning",
    )
    def onchange_show_followers_message_preview(self):
        self.show_followers_message_preview = (
            self.env["mail.mail"]
            .with_context(
                # Use current data before
                partner_format=self.show_followers_partner_format or "",
                msg_sent_to=self.show_followers_message_sent_to or "",
                msg_warn=self.show_followers_message_response_warning or "",
            )
            ._build_cc_text(
                # Sample partners
                self.env["res.partner"].search([("email", "!=", False)], limit=3),
            )
        )
