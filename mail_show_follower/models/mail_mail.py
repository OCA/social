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
        for mail_id in self.ids:
            mail = self.browse(mail_id)
            message_recipients = self.search(
                [
                    ("message_id", "=", mail.message_id),
                ]
            ).mapped("recipient_ids")
            # if the email has a model, id and it belongs to the portal group
            if mail.model and mail.res_id and group_portal:
                obj = self.env[mail.model].browse(mail.res_id)
                # those partners are obtained, who do not have a user and
                # if they do it must be a portal, we exclude internal
                # users of the system.
                if hasattr(obj, "message_follower_ids"):
                    partners_obj = (
                        obj.message_follower_ids.mapped("partner_id")
                        | message_recipients
                    )
                    # internal partners
                    user_partner_ids = (
                        self.env["res.users"]
                        .search(
                            [
                                ("active", "in", (True, False)),
                                ("show_in_cc", "=", False),
                            ]
                        )
                        .filtered(lambda x: group_portal not in x.groups_id)
                        .mapped("partner_id")
                        .ids
                    )
                    partners_len = len(
                        partners_obj.filtered(
                            lambda x: x.id not in user_partner_ids
                            and (
                                not x.user_ids
                                or group_portal in x.user_ids.mapped("groups_id")
                            )
                        )
                    )
                    if partners_len > 1:
                        # get partners
                        cc_internal = True
                        # else get company in object
                        if hasattr(obj, "company_id") and obj.company_id:
                            cc_internal = obj.company_id.show_internal_users_cc
                        # get company in user
                        elif mail.env and mail.env.user and mail.env.user.company_id:
                            cc_internal = (
                                self.env.user.company_id.show_internal_users_cc
                            )
                        if cc_internal:
                            partners = partners_obj.filtered(
                                lambda x: x.id not in user_partner_ids
                                and (
                                    not x.user_ids
                                    or any(x.mapped("user_ids.show_in_cc"))
                                )
                            )
                        else:
                            partners = partners_obj.filtered(
                                lambda x: x.id not in user_partner_ids
                                and (
                                    not x.user_ids
                                    or group_portal in x.user_ids.mapped("groups_id")
                                )
                            )
                        partners = partners.filtered(
                            lambda x: not x.user_ids
                            or x.user_ids  # otherwise, email is not sent
                            and "email" in x.user_ids.mapped("notification_type")
                        )
                        # set proper lang for recipients
                        langs = list(
                            filter(
                                bool,
                                mail.mapped("recipient_ids.lang")
                                + [
                                    mail.author_id.lang,
                                    self.env.company.partner_id.lang,
                                ],
                            )
                        )
                        # get show follower text
                        final_cc = mail.with_context(
                            lang=langs and langs[0]
                        )._build_cc_text(partners)
                        # it is saved in the body_html field so that it does
                        # not appear in the odoo log
                        mail.body_html = final_cc + mail.body_html
        return super()._send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            smtp_session=smtp_session,
        )
