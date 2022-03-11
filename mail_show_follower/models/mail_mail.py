from odoo import models


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        plain_text = (
            '<div summary="o_mail_notification" style="padding: 0px; '
            'font-size: 10px;"><b>CC</b>: %s<hr style="background-color:'
            "rgb(204,204,204);border:medium none;clear:both;display:block;"
            'font-size:0px;min-height:1px;line-height:0; margin:4px 0 12px 0;"></div>'
        )
        group_portal = self.env.ref("base.group_portal")
        for mail_id in self.ids:
            mail = self.browse(mail_id)
            # if the email has a model, id and it belongs to the portal group
            if mail.model and mail.res_id and group_portal:
                obj = self.env[mail.model].browse(mail.res_id)
                # those partners are obtained, who do not have a user and
                # if they do it must be a portal, we exclude internal
                # users of the system.
                if hasattr(obj, "message_follower_ids"):
                    partners_obj = obj.message_follower_ids.mapped("partner_id")
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
                                and (not x.user_ids or x.user_ids.show_in_cc)
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
                        # get names and emails
                        final_cc = None
                        mails = ""
                        for p in partners:
                            mails += "%s &lt;%s&gt;, " % (p.name, p.email)
                        # join texts
                        final_cc = plain_text % (mails[:-2])
                        # it is saved in the body_html field so that it does
                        # not appear in the odoo log
                        mail.body_html = final_cc + mail.body_html
        return super()._send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            smtp_session=smtp_session,
        )
