# -*- coding: utf-8 -*-
import base64
import logging
import psycopg2
from email.utils import formataddr

from odoo import _, models, fields, api, tools
from odoo.addons.base.ir.ir_mail_server import MailDeliveryException
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    _inherit = 'mail.mail'

    split_mail_by_recipients = fields.Selection([
        ('split', 'One mail for each recipient'),
        ('merge', 'One mail for all recipients'),
        ('project', 'Project Default')],
        string='Split mail by recipient partner',
        default='split',
        help='',
    )

    @api.multi
    def send_get_mail_to(self, partner=None):
        """Forge the email_to with the following heuristic:
          - if 'partner', recipient specific (Partner Name <email>)
          - else fallback on mail.email_to splitting """
        self.ensure_one()
        if partner:
            email_to = []
            for partner in partner:
                email_to.append(formataddr((partner.name, partner.email)))
        else:
            email_to = tools.email_split_and_format(self.email_to)
        return email_to

    @api.multi
    def send_get_email_dict(self, partner=None):
        """Return a dictionary for specific email values, depending on a
        partner, or generic to the whole recipients given by mail.email_to.

            :param browse_record mail: mail.mail browse_record
            :param browse_record partner: specific recipient partner
        """
        self.ensure_one()
        body = self.send_get_mail_body()
        body_alternative = tools.html2plaintext(body)
        res = {
            'body': body,
            'body_alternative': body_alternative,
            'email_to': self.send_get_mail_to(partner=partner),
        }
        return res

    @api.multi
    def send(self, auto_commit=False, raise_exception=False):
        """ Sends the selected emails immediately, ignoring their current
            state (mails that have already been sent should not be passed
            unless they should actually be re-sent).
            Emails successfully delivered are marked as 'sent', and those
            that fail to be deliver are marked as 'exception', and the
            corresponding error mail is output in the server logs.

            :param bool auto_commit: whether to force a commit of the mail 
                status after sending each mail (meant only for scheduler 
                processing); should never be True during normal transactions 
                (default: False)
            :param bool raise_exception: whether to raise an exception if the
                email sending process has failed
            :return: True
        """
        IrMailServer = self.env['ir.mail_server']

        for mail_id in self.ids:
            try:
                mail = self.browse(mail_id)
                # TDE note: remove me when model_id field is present on
                # mail.message - done here to avoid doing it multiple times
                # in the sub method
                if mail.model:
                    model = self.env['ir.model'].sudo().search(
                        [('model', '=', mail.model)])[0]
                else:
                    model = None
                if model:
                    mail = mail.with_context(model_name=model.name)

                # load attachment binary data with a separate read(), as
                # prefetching all `datas` (binary field) could bloat the
                # browse cache, triggerring
                # soft/hard mem limits with temporary data.
                attachments = [(a['datas_fname'], base64.b64decode(a['datas']))
                               for a in mail.attachment_ids.sudo().read(
                        ['datas_fname', 'datas'])]

                # specific behavior to customize the send email for notified
                # partners
                email_list = []
                default = self.env['ir.config_parameter'].get_param(
                    'default_mail_split_by_partner_conf')
                if mail.split_mail_by_recipients == 'default' \
                        and default == 'merge' \
                        or mail.split_mail_by_recipients == 'merge':
                    if mail.email_to or mail.recipient_ids:
                        email_list.append(mail.send_get_email_dict(
                                partner=mail.recipient_ids))

                if mail.split_mail_by_recipients == 'default' \
                        and default == 'split' \
                        or mail.split_mail_by_recipients == 'split':
                    if mail.email_to:
                        email_list.append(mail.send_get_email_dict())
                    for partner in mail.recipient_ids:
                        email_list.append(
                            mail.send_get_email_dict(partner=partner))


                # headers
                headers = {}
                bounce_alias = self.env['ir.config_parameter'].get_param(
                    "mail.bounce.alias")
                catchall_domain = self.env['ir.config_parameter'].get_param(
                    "mail.catchall.domain")
                if bounce_alias and catchall_domain:
                    if mail.model and mail.res_id:
                        headers['Return-Path'] = '%s+%d-%s-%d@%s' % (
                            bounce_alias, mail.id, mail.model, mail.res_id,
                            catchall_domain)
                    else:
                        headers['Return-Path'] = '%s+%d@%s' % (
                            bounce_alias, mail.id, catchall_domain)
                if mail.headers:
                    try:
                        headers.update(safe_eval(mail.headers))
                    except Exception:
                        pass

                # Writing on the mail object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure
                # earlier
                mail.write({
                    'state': 'exception',
                    'failure_reason': _(
                        'Error without exception. Probably due do sending an '
                        'email without computed recipients.'),
                })
                mail_sent = False

                # build an RFC2822 email.message.Message object and send it
                # without queuing
                res = None
                for email in email_list:
                    msg = IrMailServer.build_email(
                        email_from=mail.email_from,
                        email_to=email.get('email_to'),
                        subject=mail.subject,
                        body=email.get('body'),
                        body_alternative=email.get('body_alternative'),
                        email_cc=tools.email_split(mail.email_cc),
                        reply_to=mail.reply_to,
                        attachments=attachments,
                        message_id=mail.message_id,
                        references=mail.references,
                        object_id=mail.res_id and (
                            '%s-%s' % (mail.res_id, mail.model)),
                        subtype='html',
                        subtype_alternative='plain',
                        headers=headers)
                    try:
                        res = IrMailServer.send_email(
                            msg, mail_server_id=mail.mail_server_id.id)
                    except AssertionError as error:
                        if error.message == IrMailServer.NO_VALID_RECIPIENT:
                            # No valid recipient found for this particular
                            # mail item -> ignore error to avoid blocking
                            # delivery to next recipients, if any. If this is
                            # the only recipient, the mail will show as failed.
                            _logger.info(
                                "Ignoring invalid recipients for mail.mail %s:"
                                " %s", mail.message_id, email.get('email_to'))
                        else:
                            raise
                if res:
                    mail.write({'state': 'sent', 'message_id': res,
                                'failure_reason': False})
                    mail_sent = True

                # /!\ can't use mail.state here, as mail.refresh() will
                # cause an error
                # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr
                # in 6.1
                if mail_sent:
                    _logger.info(
                        'Mail with ID %r and Message-Id %r successfully sent',
                        mail.id, mail.message_id)
                mail._postprocess_sent_message(mail_sent=mail_sent)
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify
                # user or abort cron job
                # instead of marking the mail as failed
                _logger.exception(
                    'MemoryError while processing mail with ID %r and Msg-Id %r. Consider raising the --limit-memory-hard startup option',
                    mail.id, mail.message_id)
                raise
            except psycopg2.Error:
                # If an error with the database occurs, chances are that the cursor is unusable.
                # This will lead to an `psycopg2.InternalError` being raised when trying to write
                # `state`, shadowing the original exception and forbid a retry on concurrent
                # update. Let's bubble it.
                raise
            except Exception as e:
                failure_reason = tools.ustr(e)
                _logger.exception('failed sending mail (id: %s) due to %s',
                                  mail.id, failure_reason)
                mail.write(
                    {'state': 'exception', 'failure_reason': failure_reason})
                mail._postprocess_sent_message(mail_sent=False)
                if raise_exception:
                    if isinstance(e, AssertionError):
                        # get the args of the original error, wrap into a value and throw a MailDeliveryException
                        # that is an except_orm, with name and value as arguments
                        value = '. '.join(e.args)
                        raise MailDeliveryException(_("Mail Delivery Failed"),
                                                    value)
                    raise

            if auto_commit is True:
                self._cr.commit()
        return True
