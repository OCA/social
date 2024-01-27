# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import threading

from odoo import _, api, models, registry, SUPERUSER_ID

from .mail_mail import format_emails
from odoo.tools.misc import clean_context, split_every


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"


    # ------------------------------------------------------------
    # MAIL.MESSAGE HELPERS
    # ------------------------------------------------------------

    def _get_message_create_valid_field_names(self):
        """
        add cc and bcc field to create record in mail.mail
        """
        field_names = super()._get_message_create_valid_field_names()
        field_names.update({"recipient_cc_ids", "recipient_bcc_ids"})
        return field_names

    # ------------------------------------------------------
    # NOTIFICATION API
    # ------------------------------------------------------

    def _notify_by_email_get_base_mail_values(self, message, additional_values=None):
        """
        This is to add cc, bcc addresses to mail.mail objects so that email
        can be sent to those addresses.
        """
        res = super()._notify_by_email_get_base_mail_values(
            message, additional_values=additional_values
        )
        partners_cc = (
            message.parent_id.recipient_cc_ids
            if message.parent_id.recipient_cc_ids
            else None
        )
        if message.recipient_cc_ids not in partners_cc:
            partners_cc |= message.recipient_cc_ids

        if partners_cc:
            res["email_cc"] = format_emails(partners_cc)

        partners_bcc = (
            message.parent_id.recipient_bcc_ids
            if message.parent_id.recipient_bcc_ids
            else None
        )
        if message.recipient_bcc_ids not in partners_cc:
            partners_bcc |= message.recipient_bcc_ids

        if partners_bcc:
            res["email_bcc"] = format_emails(partners_bcc)
        return res


    def _notify_get_recipients_classify(self, message, recipients_data, model_description, msg_vals=None):
        res = super()._notify_get_recipients_classify(
            message, recipients_data, model_description, msg_vals=msg_vals
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


    def _notify_thread_by_email(
        self,
        message,
        recipients_data,
        msg_vals=False,
        mail_auto_delete=True,  # mail.mail
        model_description=False,
        force_email_company=False,
        force_email_lang=False,  # rendering
        subtitles=None,  # rendering
        resend_existing=False,
        force_send=True,
        send_after_commit=True,  # email send
        **kwargs):
        """
        add check to avoid violates unique constraint
        """
        partners_data = [r for r in recipients_data if r["notif"] == "email"]
        if not partners_data:
            return True

        base_mail_values = self._notify_by_email_get_base_mail_values(
            message, additional_values={"auto_delete": mail_auto_delete}
        )

        # Clean the context to get rid of residual default_* keys that could cause issues during
        # the mail.mail creation.
        # Example: 'default_state' would refer to the default state of a previously created record
        # from another model that in turns triggers an assignation notification that ends up here.
        # This will lead to a traceback when trying to create a mail.mail with this state value that
        # doesn't exist.
        SafeMail = (
            self.env["mail.mail"].sudo().with_context(clean_context(self._context))
        )
        SafeNotification = (
            self.env["mail.notification"]
            .sudo()
            .with_context(clean_context(self._context))
        )
        emails = self.env["mail.mail"].sudo()

        # loop on groups (customer, portal, user,  ... + model specific like group_sale_salesman)
        notif_create_values = []
        recipients_max = 50
        for (
            _lang,
            render_values,
            recipients_group,
        ) in self._notify_get_classified_recipients_iterator(
            message,
            partners_data,
            msg_vals=msg_vals,
            model_description=model_description,
            force_email_company=force_email_company,
            force_email_lang=force_email_lang,
            subtitles=subtitles,
        ):
            # generate notification email content
            mail_body = self._notify_by_email_render_layout(
                message,
                recipients_group,
                msg_vals=msg_vals,
                render_values=render_values,
            )
            recipients_ids = recipients_group.pop("recipients")

            # create email
            for recipients_ids_chunk in split_every(recipients_max, recipients_ids):
                mail_values = self._notify_by_email_get_final_mail_values(
                    recipients_ids_chunk,
                    base_mail_values,
                    additional_values={"body_html": mail_body},
                )
                new_email = SafeMail.create(mail_values)

                if new_email and recipients_ids_chunk:
                    tocreate_recipient_ids = list(recipients_ids_chunk)
                    if resend_existing:
                        existing_notifications = (
                            self.env["mail.notification"]
                            .sudo()
                            .search(
                                [
                                    ("mail_message_id", "=", message.id),
                                    ("notification_type", "=", "email"),
                                    ("res_partner_id", "in", tocreate_recipient_ids),
                                ]
                            )
                        )
                        if existing_notifications:
                            tocreate_recipient_ids = [
                                rid
                                for rid in recipients_ids_chunk
                                if rid
                                not in existing_notifications.mapped(
                                    "res_partner_id.id"
                                )
                            ]
                            existing_notifications.write(
                                {
                                    "notification_status": "ready",
                                    "mail_mail_id": new_email.id,
                                }
                            )
                    # TODO: check if this check is needed or can be fixed from somewhere
                    visited = set()
                    for recipient_id in tocreate_recipient_ids:
                        if (recipient_id, message.id) in visited:
                            continue
                        else:
                            notif_create_values += [
                                {
                                    "author_id": message.author_id.id,
                                    "is_read": True,  # discard Inbox notification
                                    "mail_mail_id": new_email.id,
                                    "mail_message_id": message.id,
                                    "notification_status": "ready",
                                    "notification_type": "email",
                                    "res_partner_id": recipient_id,
                                }
                            ]
                            visited.add((recipient_id, message.id))
                emails += new_email

        if notif_create_values:
            SafeNotification.create(notif_create_values)

        # NOTE:
        #   1. for more than 50 followers, use the queue system
        #   2. do not send emails immediately if the registry is not loaded,
        #      to prevent sending email during a simple update of the database
        #      using the command-line.
        test_mode = getattr(threading.current_thread(), "testing", False)
        force_send = self.env.context.get("mail_notify_force_send", force_send)
        if (
            force_send
            and len(emails) < recipients_max
            and (not self.pool._init or test_mode)
        ):
            # unless asked specifically, send emails after the transaction to
            # avoid side effects due to emails being sent while the transaction fails
            if not test_mode and send_after_commit:
                email_ids = emails.ids
                dbname = self.env.cr.dbname
                _context = self._context

                @self.env.cr.postcommit.add
                def send_notifications():
                    db_registry = registry(dbname)
                    with db_registry.cursor() as cr:
                        env = api.Environment(cr, SUPERUSER_ID, _context)
                        env["mail.mail"].browse(email_ids).send()

            else:
                emails.send()

        return True
