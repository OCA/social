import ast
import base64
import logging
import re
import smtplib

import psycopg2

from odoo import _, fields, models, tools

from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)


def format_emails(partners):
    emails = [tools.formataddr((p.name, p.email)) for p in partners if p.email]
    return ", ".join(emails)


class MailMail(models.Model):
    _inherit = "mail.mail"

    email_bcc = fields.Char("Bcc", help="Blind Cc message recipients")

    def _send(  # noqa: max-complexity: 4
        self, auto_commit=False, raise_exception=False, smtp_session=None
    ):
        env = self.env
        IrMailServer = env["ir.mail_server"]
        IrAttachment = env["ir.attachment"]
        ICP = env["ir.config_parameter"].sudo()
        # Mail composer only sends 1 mail at a time.
        is_out_of_scope = len(self.ids) > 1
        is_from_composer = self.env.context.get("is_from_composer", False)
        if is_out_of_scope or not is_from_composer:
            return super()._send(
                auto_commit=auto_commit,
                raise_exception=raise_exception,
                smtp_session=smtp_session,
            )
        mail = self
        success_pids = []
        failure_type = None
        # ===== Same with native Odoo =====
        # https://github.com/odoo/odoo/blob/28e1e01835c0df2ad6e9ddf131dd438fcf6072e1
        # /addons/mail/models/mail_mail.py#L402
        try:
            if mail.state != "outgoing":
                if mail.state != "exception" and mail.auto_delete:
                    mail.sudo().unlink()
                return True

            # remove attachments if user send the link with the access_token
            body = mail.body_html or ""
            attachments = mail.attachment_ids
            for link in re.findall(r"/web/(?:content|image)/([0-9]+)", body):
                attachments = attachments - IrAttachment.browse(int(link))

            # load attachment binary data with a separate read(), as
            # prefetching all `datas` (binary field) could bloat the browse
            # cache, triggerring soft/hard mem limits with temporary data.
            attachments = [
                (a["name"], base64.b64decode(a["datas"]), a["mimetype"])
                for a in attachments.sudo().read(["name", "datas", "mimetype"])
                if a["datas"] is not False
            ]

            # ===== Different than native Odoo =====
            email = mail._send_prepare_values()
            # ===== Same with native Odoo =====
            # headers
            headers = {}
            bounce_alias = ICP.get_param("mail.bounce.alias")
            catchall_domain = ICP.get_param("mail.catchall.domain")
            if bounce_alias and catchall_domain:
                headers["Return-Path"] = "%s@%s" % (bounce_alias, catchall_domain)
            if mail.headers:
                try:
                    headers.update(ast.literal_eval(mail.headers))
                except Exception as e:
                    # ===== Different than native Odoo =====
                    _logger.warning("Error during update headers: %s" % e)

            # ===== Same with native Odoo =====
            # Writing on the mail object may fail (e.g. lock on user) which
            # would trigger a rollback *after* actually sending the email.
            # To avoid sending twice the same email, provoke the failure earlier
            mail.write(
                {
                    "state": "exception",
                    "failure_reason": _(
                        "Error without exception. Probably due do sending an email"
                        " without computed recipients."
                    ),
                }
            )
            # Update notification in a transient exception state to avoid concurrent
            # update in case an email bounces while sending all emails related to current
            # mail record.
            notifs = self.env["mail.notification"].search(
                [
                    ("notification_type", "=", "email"),
                    ("mail_mail_id", "in", mail.ids),
                    ("notification_status", "not in", ("sent", "canceled")),
                ]
            )
            if notifs:
                notif_msg = _(
                    "Error without exception. Probably due do concurrent access"
                    " update of notification records. Please see with an administrator."
                )
                notifs.sudo().write(
                    {
                        "notification_status": "exception",
                        "failure_type": "unknown",
                        "failure_reason": notif_msg,
                    }
                )
                # `test_mail_bounce_during_send`, force immediate update to obtain the lock.
                # see rev. 56596e5240ef920df14d99087451ce6f06ac6d36
                notifs.flush(
                    fnames=["notification_status", "failure_type", "failure_reason"],
                    records=notifs,
                )

            # protect against ill-formatted email_from when formataddr was used on an already formatted email # noqa: B950
            emails_from = tools.email_split_and_format(mail.email_from)
            email_from = emails_from[0] if emails_from else mail.email_from

            # build an RFC2822 email.message.Message object and send it without queuing
            res = None
            # TDE note: could be great to pre-detect missing to/cc and skip sending it
            # to go directly to failed state update
            # ===== Different than native Odoo =====
            # support headers specific to the specific outgoing email
            if email.get("headers"):
                email_headers = headers.copy()
                try:
                    email_headers.update(email.get("headers"))
                except Exception as e:
                    _logger.warning("Error during email_headers update: %s", e)
            else:
                email_headers = headers
            email["email_from"] = email_from
            msg = self.build_email(
                email,
                attachments=attachments,
                headers=email_headers,
            )
            try:
                res = IrMailServer.send_email(
                    msg,
                    mail_server_id=mail.mail_server_id.id,
                    smtp_session=smtp_session,
                )
                success_pids += mail.recipient_ids.ids
            # ===== Same with native Odoo =====
            except AssertionError as error:
                if str(error) == IrMailServer.NO_VALID_RECIPIENT:
                    # if we have a list of void emails for email_list
                    # -> email missing, otherwise generic email
                    # failure
                    if (
                        not email.get("email_to")
                        and failure_type != "mail_email_invalid"
                    ):
                        failure_type = "mail_email_missing"
                    else:
                        failure_type = "mail_email_invalid"
                    # No valid recipient found for this particular
                    # mail item -> ignore error to avoid blocking
                    # delivery to next recipients, if any. If this is
                    # the only recipient, the mail will show as failed.
                    _logger.info(
                        "Ignoring invalid recipients for mail.mail %s: %s",
                        mail.message_id,
                        email.get("email_to"),
                    )
                else:
                    raise
            if res:  # mail has been sent at least once, no major exception occurred
                mail.write(
                    {"state": "sent", "message_id": res, "failure_reason": False}
                )
                _logger.info(
                    "Mail with ID %r and Message-Id %r successfully sent",
                    mail.id,
                    mail.message_id,
                )
                # /!\ can't use mail.state here, as mail.refresh() will cause an error
                # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr in 6.1
            mail._postprocess_sent_message(
                success_pids=success_pids, failure_type=failure_type
            )
        except MemoryError:
            # prevent catching transient MemoryErrors, bubble up to
            # notify user or abort cron job instead of marking the
            # mail as failed
            _logger.exception(
                "MemoryError while processing mail with ID %r and Msg-Id %r."
                " Consider raising the --limit-memory-hard startup option",
                mail.id,
                mail.message_id,
            )
            # mail status will stay on ongoing since transaction will be rollback
            raise
        except (psycopg2.Error, smtplib.SMTPServerDisconnected):
            # If an error with the database or SMTP session occurs,
            # chances are that the cursor or SMTP session are
            # unusable, causing further errors when trying to save the
            # state.
            _logger.exception(
                "Exception while processing mail with ID %r and Msg-Id %r.",
                mail.id,
                mail.message_id,
            )
            raise
        except Exception as e:
            failure_reason = tools.ustr(e)
            _logger.exception(
                "failed sending mail (id: %s) due to %s", mail.id, failure_reason
            )
            mail.write({"state": "exception", "failure_reason": failure_reason})
            mail._postprocess_sent_message(
                success_pids=success_pids,
                failure_reason=failure_reason,
                failure_type="unknown",
            )
            if raise_exception:
                if isinstance(e, (AssertionError, UnicodeEncodeError)):
                    if isinstance(e, UnicodeEncodeError):
                        value = "Invalid text: %s" % e.object
                    else:
                        value = ". ".join(e.args)
                    raise MailDeliveryException(value) from e
                raise

        # ===== Different than native Odoo =====
        # As we only send one email, auto_commit has no value
        return True

    def build_email(self, email, attachments=None, headers=None):
        env = self.env
        mail = self
        email_from = email.get("email_from")
        IrMailServer = env["ir.mail_server"]
        # ===== Same with native Odoo =====
        # https://github.com/odoo/odoo/blob/28e1e01835c0df2ad6e9ddf131dd438fcf6072e1
        # /addons/mail/models/mail_mail.py#L486
        msg = IrMailServer.build_email(
            email_from=email_from,
            email_to=email.get("email_to"),
            subject=mail.subject,
            body=email.get("body"),
            body_alternative=email.get("body_alternative"),
            # ===== Different than native Odoo =====
            email_cc=mail.email_cc,
            email_bcc=mail.email_bcc,
            # ===== Same with native Odoo =====
            reply_to=mail.reply_to,
            attachments=attachments,
            message_id=mail.message_id,
            references=mail.references,
            object_id=mail.res_id and ("%s-%s" % (mail.res_id, mail.model)),
            subtype="html",
            subtype_alternative="plain",
            headers=headers,
        )
        return msg

    def _send_prepare_values(self, partner=None):
        res = super()._send_prepare_values(partner=partner)
        is_from_composer = self.env.context.get("is_from_composer", False)
        if not is_from_composer:
            return res
        partners_cc_bcc = self.recipient_cc_ids + self.recipient_bcc_ids
        partner_to_ids = [r.id for r in self.recipient_ids if r not in partners_cc_bcc]
        partner_to = self.env["res.partner"].browse(partner_to_ids)
        res["email_to"] = format_emails(partner_to)
        res["email_cc"] = format_emails(self.recipient_cc_ids)
        res["email_bcc"] = format_emails(self.recipient_bcc_ids)
        return res
