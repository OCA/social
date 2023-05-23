# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from .mail_mail import format_emails


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_create(self, values_list):
        context = self.env.context
        res = super()._message_create(values_list)
        partners_cc = context.get("partner_cc_ids", None)
        if partners_cc:
            res.recipient_cc_ids = partners_cc
        partners_bcc = context.get("partner_bcc_ids", None)
        if partners_bcc:
            res.recipient_bcc_ids = partners_bcc
        return res

    def _notify_by_email_add_values(self, base_mail_values):
        """
        This is to add cc, bcc addresses to mail.mail objects so that email
        can be sent to those addresses.
        """
        context = self.env.context

        partners_cc = context.get("partner_cc_ids", None)
        if partners_cc:
            base_mail_values["email_cc"] = format_emails(partners_cc)
        partners_bcc = context.get("partner_bcc_ids", None)
        if partners_bcc:
            base_mail_values["email_bcc"] = format_emails(partners_bcc)
        res = super()._notify_by_email_add_values(base_mail_values)
        return res

    def _notify_compute_recipients(self, message, msg_vals):
        """
        This is to add cc, bcc recipients so that they can be grouped with
        other recipients.
        """
        ResPartner = self.env["res.partner"]
        MailFollowers = self.env["mail.followers"]
        rdata = super()._notify_compute_recipients(message, msg_vals)
        context = self.env.context
        is_from_composer = context.get("is_from_composer", False)
        if not is_from_composer:
            return rdata
        for pdata in rdata:
            pdata["type"] = "customer"
        partners_cc_bcc = context.get("partner_cc_ids", ResPartner)
        partners_cc_bcc += context.get("partner_bcc_ids", ResPartner)
        msg_sudo = message.sudo()
        message_type = (
            msg_vals.get("message_type") if msg_vals else msg_sudo.message_type
        )
        subtype_id = msg_vals.get("subtype_id") if msg_vals else msg_sudo.subtype_id.id
        recipients_cc_bcc = MailFollowers._get_recipient_data(
            None, message_type, subtype_id, partners_cc_bcc.ids
        )
        for pid, active, pshare, notif, groups in recipients_cc_bcc:
            if not pid:
                continue
            if not notif:  # notif is False, has no user, is therefore customer
                notif = "email"
            msg_type = "customer"
            pdata = {
                "id": pid,
                "active": active,
                "share": pshare,
                "groups": groups or [],
                "notif": notif,
                "type": msg_type,
            }
            rdata.append(pdata)
        return rdata

    def _notify_email_recipient_values(self, recipient_ids):
        """
        This is to add cc, bcc recipients' ids to recipient_ids of mail.mail
        """
        res = super()._notify_email_recipient_values(recipient_ids)
        context = self.env.context
        r_ids = list(recipient_ids)
        partners_cc = context.get("partner_cc_ids", None)
        if partners_cc:
            r_ids += partners_cc.ids
        partners_bcc = context.get("partner_bcc_ids", None)
        if partners_bcc:
            r_ids += partners_bcc.ids
        if partners_cc or partners_bcc:
            res["recipient_ids"] = tuple(set(r_ids))
        return res

    def _notify_classify_recipients(self, recipient_data, model_name, msg_vals=None):
        res = super()._notify_classify_recipients(
            recipient_data, model_name, msg_vals=msg_vals
        )
        is_from_composer = self.env.context.get("is_from_composer", False)
        if not is_from_composer:
            return res
        ids = []
        customer_data = None
        for rcpt_data in res:
            if rcpt_data["notification_group_name"] == "customer":
                customer_data = rcpt_data
            else:
                ids += rcpt_data["recipients"]
        if not customer_data:
            customer_data = res[0]
            customer_data["notification_group_name"] = "customer"
            customer_data["recipients"] = ids
        else:
            customer_data["recipients"] += ids
        return [customer_data]
