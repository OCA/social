# Copyright 2016-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api, tools
from odoo.tools.config import config
from odoo.tools.safe_eval import safe_eval

from sendgrid.helpers.mail import (
    Mail, From, To, Cc, Bcc, Subject, Substitution, Header,
    CustomArg, SendAt, Content, MimeType, Attachment, FileName,
    FileContent, FileType, Disposition, ContentId, TemplateId,
    Section, ReplyTo, Category, BatchId, Asm, GroupId, GroupsToDisplay,
    IpPoolName, MailSettings, BccSettings, BccSettingsEmail,
    BypassListManagement, FooterSettings, FooterText,
    FooterHtml, SandBoxMode, SpamCheck, SpamThreshold, SpamUrl,
    TrackingSettings, ClickTracking, SubscriptionTracking,
    SubscriptionText, SubscriptionHtml, SubscriptionSubstitutionTag,
    OpenTracking, OpenTrackingSubstitutionTag, Ganalytics,
    UtmSource, UtmMedium, UtmTerm, UtmContent, UtmCampaign)

import logging
import re
import time

_logger = logging.getLogger(__name__)

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Email, Attachment, CustomArg, Content, \
        Personalization, Substitution, Mail, Header
except ImportError:
    _logger.info("ImportError raised while loading module.")
    _logger.debug("ImportError details:", exc_info=True)

STATUS_OK = 202


class MailMail(models.Model):
    """ Email message sent through SendGrid """
    _inherit = 'mail.mail'

    tracking_email_ids = fields.One2many(
        'mail.tracking.email', 'mail_id', string='Registered events',
        readonly=True)
    click_count = fields.Integer(
        compute='_compute_tracking', store=True, readonly=True)
    opened = fields.Boolean(
        compute='_compute_tracking', store=True, readonly=True)
    tracking_event_ids = fields.One2many(
        'mail.tracking.event', compute='_compute_events')
    dynamic_template_selected = fields.Boolean(compute='_compute_dynamic_template_selected')

    @api.depends('tracking_email_ids', 'tracking_email_ids.click_count',
                 'tracking_email_ids.state')
    def _compute_tracking(self):
        for email in self:
            click_count = sum(email.tracking_email_ids.mapped(
                'click_count'))
            opened = self.env['mail.tracking.email'].search_count([
                ('state', '=', 'opened'),
                ('mail_id', '=', email.id)
            ])
            email.update({
                'click_count': click_count,
                'opened': opened > 0
            })

    def _compute_dynamic_template_selected(self):
        for email in self:
            self.dynamic_template_selected = True if email.sendgrid_template_id.generation == 'dynamic' else False

    def _compute_events(self):
        for email in self:
            email.tracking_event_ids = email.tracking_email_ids.mapped(
                'tracking_event_ids')

    @api.multi
    def send(self, auto_commit=False, raise_exception=False):
        """ Override send to select the method to send the e-mail. """
        traditional = self.filtered(lambda e: e.send_method == 'traditional')
        sendgrid = self.filtered(lambda e: e.send_method == 'sendgrid')
        if traditional:
            super(MailMail, traditional).send(auto_commit, raise_exception)
        if sendgrid:
            sendgrid.send_sendgrid()
        return True

    @api.multi
    def send_sendgrid(self):
        """ Use sendgrid transactional e-mails : e-mails are sent one by
        one. """
        outgoing = self.filtered(lambda em: em.state == 'outgoing')
        api_key = config.get('sendgrid_api_key')
        if outgoing and not api_key:
            _logger.error(
                'Missing sendgrid_api_key in conf file. Skipping Sendgrid '
                'send.'
            )
            return

        sg = SendGridAPIClient(api_key)
        for email in outgoing:
            try:
                message = email._prepare_sendgrid_data().get()
                response = sg.send(message)
            except Exception as e:
                _logger.error(e.message or "mail not sent.", exc_info=True)
                continue

            status = response.status_code
            msg = response.body

            if status == STATUS_OK:
                _logger.info("e-mail sent. " + str(msg))
                email._track_sendgrid_emails()
                email.write({
                    'sent_date': fields.Datetime.now(),
                    'state': 'sent'
                })
                if not self.env.context.get('test_mode'):
                    # Commit at each e-mail processed to avoid any errors
                    # invalidating state.
                    self.env.cr.commit()  # pylint: disable=invalid-commit

                email._postprocess_sent_message(mail_sent=True)
            else:
                email._postprocess_sent_message(mail_sent=False)
                _logger.error("Failed to send email: {}".format(str(msg)))

    def _prepare_sendgrid_data(self):
        """
        Prepare and creates the Sendgrid Email object
        :return: sendgrid.helpers.mail.Email object
        """
        self.ensure_one()
        s_mail = Mail()
        s_mail.from_email = From(self.email_from)
        if self.reply_to:
            s_mail.reply_to = ReplyTo(self.reply_to)

        # Add custom fields to match the tracking
        s_mail.custom_arg = CustomArg('odoo_id', self.message_id)
        s_mail.custom_arg = CustomArg('odoo_db', self.env.cr.dbname)

        headers = {
            'Message-Id': self.message_id
        }
        if self.headers:
            try:
                headers.update(safe_eval(self.headers))
            except Exception:
                pass
        for h_name, h_val in headers.items():
            s_mail.header = Header(h_name, h_val)

        html = self.body_html or ' '

        p = re.compile(r'<.*?>')  # Remove HTML markers
        text_only = self.body_text or p.sub('', html.replace('<br/>', '\n'))

        s_mail.content = Content(MimeType.text, text_only or ' ')
        s_mail.content = Content(MimeType.html, html)

        test_address = config.get('sendgrid_test_address')

        s_mail.subject = Subject(self.subject or "(No subject)")

        addresses = set()
        if not test_address:
            if self.email_to:
                addresses = set(self.email_to.split(','))
                for address in addresses:
                    s_mail.to = To(address)
            for recipient in self.recipient_ids:
                if recipient.email not in addresses:
                    s_mail.to = To(recipient.email)
                    addresses.add(recipient.email)
            if self.email_cc and self.email_cc not in addresses:
                s_mail.cc = Cc(self.email_cc)
        else:
            _logger.info('Sending email to test address {}'.format(test_address))
            s_mail.to = To(test_address)
            self.email_to = test_address

        if self.sendgrid_template_id:
            s_mail.template_id = TemplateId(self.sendgrid_template_id.remote_id)
            s_mail.template_generation = self.sendgrid_template_id.generation

            if s_mail.template_generation == 'dynamic':
                substitutions_dict = {}
                for substitution in self.substitution_ids:
                    substitutions_dict.update({substitution.key: substitution.value})

                substitutions_dict.update({'subject': self.subject or "(No subject)"})
                substitutions_dict.update({'body': html})
                s_mail.dynamic_template_data = substitutions_dict
            else:
                for substitution in self.substitution_ids:
                    s_mail.substitution = Substitution('{' + substitution.key + '}', substitution.value)

        for attachment in self.attachment_ids:
            # Datas are not encoded properly for sendgrid
            s_attachment = Attachment(
                FileContent(attachment.datas.decode('utf-8')),
                FileName(attachment.name),
                FileType(attachment.mimetype),
                Disposition('attachment')
            )
            s_mail.attachment = s_attachment

        return s_mail

    def _track_sendgrid_emails(self):
        """ Create tracking e-mails after successfully sent with Sendgrid. """
        self.ensure_one()
        m_tracking = self.env['mail.tracking.email'].sudo()
        track_vals = self._prepare_sendgrid_tracking()
        for recipient in tools.email_split_and_format(self.email_to):
            track_vals['recipient'] = recipient
            m_tracking += m_tracking.create(track_vals)
        for partner in self.recipient_ids:
            track_vals.update({
                'partner_id': partner.id,
                'recipient': partner.email,
            })
            m_tracking += m_tracking.create(track_vals)
        return m_tracking

    def _prepare_sendgrid_tracking(self):
        ts = time.time()
        return {
            'name': self.subject,
            'timestamp': '%.6f' % ts,
            'time': fields.Datetime.now(),
            'mail_id': self.id,
            'mail_message_id': self.mail_message_id.id,
            'sender': self.email_from,
        }

    def update_substitutions(self):
        template = self.sendgrid_template_id

        new_substitutions = []
        keywords = template.get_keywords()
        substitutions = self.substitution_ids
        # Add new keywords from the sendgrid template
        for key in keywords:
            if key not in substitutions.mapped('key'):
                substitution_vals = {
                    'key': key
                }
                new_substitutions.append((0, 0, substitution_vals))

        self.write({'substitution_ids': new_substitutions})
