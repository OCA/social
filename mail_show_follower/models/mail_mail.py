from markupsafe import Markup

from odoo import api, models, tools


class MailMail(models.Model):
    _inherit = "mail.mail"

    @api.model
    def _build_cc_text(self, partners):
        if not partners:
            return ""

        def get_ctx_param(ctx_key, default_parm):
            if ctx_key in self.env.context:
                return self.env.context[ctx_key]
            return default_parm

        def remove_p(markup_txt):
            if markup_txt.startswith("<p>") and markup_txt.endswith("</p>"):
                return markup_txt[3:-4]
            return markup_txt

        company = self.env.company
        partner_format = get_ctx_param(
            "partner_format", company.show_followers_partner_format
        )
        msg_sent_to = get_ctx_param(
            "msg_sent_to", company.show_followers_message_sent_to
        )
        msg_warn = get_ctx_param(
            "msg_warn", company.show_followers_message_response_warning
        )
        partner_message = ", ".join(
            [
                partner_format
                % {
                    # Supported parameters
                    "partner_name": p.name,
                    "partner_email": p.email,
                    "partner_email_domain": tools.email_domain_extract(p.email),
                }
                for p in partners
            ]
        )
        full_text = """
            <div summary='o_mail_notification' style='padding:5px;
            margin:10px 0px 10px 0px;font-size:13px;border-radius:5px;
            font-family:Arial;border:1px solid #E0E2E6;background-color:#EBEBEB;'>
            {msg_sent_to} {partner_message}
            {rc}{msg_warn}
            </div>
        """.format(
            msg_sent_to=remove_p(msg_sent_to),
            partner_message=Markup.escape(partner_message),
            rc=msg_warn.striptags() and "<br/>" or "",
            msg_warn=msg_warn.striptags() and remove_p(msg_warn) or "",
        )
        return full_text

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        group_portal = self.env.ref("base.group_portal")

        for mail in self:
            if not (mail.model and mail.res_id and group_portal):
                continue
            recipients = mail.recipient_ids | mail.notified_partner_ids
            record = self.env[mail.model].browse(mail.res_id)
            company = (
                record.company_id
                if hasattr(record, "company_id")
                else self.env.user.company_id
            )
            show_internal_users = company and company.show_internal_users_cc
            show_in_cc_recipients = recipients.filtered(
                lambda r: r._show_in_cc(show_internal_users)
            )
            if len(show_in_cc_recipients) <= 1:
                continue

            langs = (
                mail.recipient_ids.mapped("lang")
                or mail.author_id.lang
                or self.env.company.partner_id.lang
            )
            final_cc = mail.with_context(lang=langs[0])._build_cc_text(
                show_in_cc_recipients
            )
            mail.body_html = final_cc + mail.body_html

        return super()._send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            smtp_session=smtp_session,
        )
