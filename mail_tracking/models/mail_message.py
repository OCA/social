# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models, api, fields
from odoo.tools import email_split


class MailMessage(models.Model):
    _inherit = "mail.message"

    # Recipients
    email_cc = fields.Char("Cc", help='Additional recipients that receive a '
                                      '"Carbon Copy" of the e-mail')
    mail_tracking_ids = fields.One2many(
        comodel_name='mail.tracking.email',
        inverse_name='mail_message_id',
        string="Mail Trackings",
    )
    mail_tracking_needs_action = fields.Boolean(
        help="The message tracking will be considered"
             " to filter tracking issues",
        default=False,
    )
    is_failed_message = fields.Boolean(compute="_compute_is_failed_message")

    def get_failed_states(self):
        """The 'failed' states of the message"""
        return {'error', 'rejected', 'spam', 'bounced', 'soft-bounced'}

    @api.depends('mail_tracking_needs_action', 'author_id', 'partner_ids',
                 'mail_tracking_ids')
    def _compute_is_failed_message(self):
        """Compute 'is_failed_message' field for the active user"""
        failed_states = self.get_failed_states()
        for record in self:
            needs_action = record.mail_tracking_needs_action
            involves_me = record.env.user.partner_id.id in (
                record.author_id | record.partner_ids).ids
            has_failed_trackings = failed_states.intersection(
                record.mapped("mail_tracking_ids.state"))
            record.is_failed_message = bool(
                needs_action and involves_me and has_failed_trackings)

    def _tracking_status_map_get(self):
        """Map tracking states to be used in chatter"""
        return {
            'False': 'waiting',
            'error': 'error',
            'deferred': 'sent',
            'sent': 'sent',
            'delivered': 'delivered',
            'opened': 'opened',
            'rejected': 'error',
            'spam': 'error',
            'unsub': 'opened',
            'bounced': 'error',
            'soft-bounced': 'error',
        }

    def _partner_tracking_status_get(self, tracking_email):
        """Determine tracking status"""
        tracking_status_map = self._tracking_status_map_get()
        status = 'unknown'
        if tracking_email:
            tracking_email_status = str(tracking_email.state)
            status = tracking_status_map.get(tracking_email_status, 'unknown')
        return status

    def _partner_tracking_status_human_get(self, status):
        """Translations for tracking statuses to be used on qweb"""
        statuses = {'waiting': _('Waiting'), 'error': _('Error'),
                    'sent': _('Sent'), 'delivered': _('Delivered'),
                    'opened': _('Opened'), 'unknown': _('Unknown')}
        return _("Status: %s") % statuses[status]

    @api.model
    def _get_error_description(self, tracking):
        """Translations for error descriptions to be used on qweb"""
        descriptions = {
            'no_recipient': _("The partner doesn't have a defined email"),
        }
        return descriptions.get(tracking.error_type,
                                tracking.error_description)

    def tracking_status(self):
        """Generates a complete status tracking of the messages by partner"""
        res = {}
        for message in self:
            partner_trackings = []
            partners_already = self.env['res.partner']
            partners = self.env['res.partner']
            trackings = self.env['mail.tracking.email'].sudo().search([
                ('mail_message_id', '=', message.id),
            ])
            # Get Cc recipients
            email_cc_list = email_split(message.email_cc)
            if any(email_cc_list):
                partners |= partners.search([('email', 'in', email_cc_list)])
            email_cc_list = set(email_cc_list)
            # Search all trackings for this message
            for tracking in trackings:
                status = self._partner_tracking_status_get(tracking)
                recipient = (
                    tracking.partner_id.name or tracking.recipient)
                partner_trackings.append({
                    'status': status,
                    'status_human':
                        self._partner_tracking_status_human_get(status),
                    'error_type': tracking.error_type,
                    'error_description':
                        self._get_error_description(tracking),
                    'tracking_id': tracking.id,
                    'recipient': recipient,
                    'partner_id': tracking.partner_id.id,
                    'isCc': False,
                })
                if tracking.partner_id:
                    email_cc_list.discard(tracking.partner_id.email)
                    partners_already |= tracking.partner_id
            # Search all recipients for this message
            if message.partner_ids:
                partners |= message.partner_ids
            if message.needaction_partner_ids:
                partners |= message.needaction_partner_ids
            # Remove recipients already included
            partners -= partners_already
            tracking_unkown_values = {
                'status': 'unknown',
                'status_human':  self._partner_tracking_status_human_get(
                    'unknown'),
                'error_type': False,
                'error_description': False,
                'tracking_id': False,
            }
            for partner in partners:
                # If there is partners not included, then status is 'unknown'
                # and perhaps a Cc recipient
                isCc = False
                if partner.email in email_cc_list:
                    email_cc_list.discard(partner.email)
                    isCc = True
                tracking_unkown_values.update({
                    'recipient': partner.name,
                    'partner_id': partner.id,
                    'isCc': isCc,
                })
                partner_trackings.append(tracking_unkown_values.copy())
            for email in email_cc_list:
                # If there is Cc without partner
                tracking_unkown_values.update({
                    'recipient': email,
                    'partner_id': False,
                    'isCc': True,
                })
                partner_trackings.append(tracking_unkown_values.copy())
            res[message.id] = {
                'partner_trackings': partner_trackings,
                'is_failed_message': message.is_failed_message,
            }
        return res

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        """Preare values to be used by the chatter widget"""
        res = super(MailMessage, self)._message_read_dict_postprocess(
            messages, message_tree)
        mail_message_ids = {m.get('id') for m in messages if m.get('id')}
        mail_messages = self.browse(mail_message_ids)
        tracking_statuses = mail_messages.tracking_status()
        for message_dict in messages:
            mail_message_id = message_dict.get('id', False)
            if mail_message_id:
                message_dict.update(tracking_statuses[mail_message_id])
        return res

    @api.model
    def _prepare_dict_failed_message(self, message):
        """Preare values to be used by the chatter widget"""
        failed_trackings = message.mail_tracking_ids.filtered(
            lambda x: x.state in self.get_failed_states())
        failed_partners = failed_trackings.mapped('partner_id')
        failed_recipients = failed_partners.name_get()
        if message.author_id:
            author = message.author_id.name_get()[0]
        else:
            author = (-1, _('-Unknown Author-'))
        return {
            'id': message.id,
            'date': message.date,
            'author': author,
            'body': message.body,
            'failed_recipients': failed_recipients,
        }

    @api.multi
    def get_failed_messages(self):
        """Returns the list of failed messages to be used by the
           failed_messages widget"""
        return [self._prepare_dict_failed_message(msg)
                for msg in self.sorted('date', reverse=True)]

    @api.multi
    def toggle_tracking_status(self):
        """Toggle message tracking action needed to ignore them in the tracking
           issues filter"""
        self.mail_tracking_needs_action = not self.mail_tracking_needs_action
        return self.mail_tracking_needs_action

    @api.model
    def _get_failed_message_domain(self):
        """Returns the domain used to filter messages on discuss thread"""
        domain = self.env['mail.thread']._get_failed_message_domain()
        domain += [
            '|',
            ('partner_ids', 'in', [self.env.user.partner_id.id]),
            ('author_id', '=', self.env.user.partner_id.id),
        ]
        return domain

    @api.model
    def get_failed_count(self):
        """ Gets the number of failed messages used on discuss mailbox item"""
        return self.search_count(self._get_failed_message_domain())

    @api.model
    def message_fetch(self, domain, limit=20):
        """Force domain to be used on discuss thread messages"""
        # HACK: Because can't modify the domain in discuss JS to search the
        # failed messages we force the change here to clean it of
        # not valid criterias
        if self.env.context.get('filter_failed_message'):
            domain = self._get_failed_message_domain()
        return super().message_fetch(domain, limit=limit)

    @api.multi
    def message_format(self):
        """Adds 'failed_recipients' to display on 'failed_messages' widget"""
        message_values = super().message_format()
        for message in message_values:
            message_id = self.browse(message['id'])
            if message_id:
                failed_trackings = message_id.mail_tracking_ids.filtered(
                    lambda x: x.state in self.get_failed_states())
                failed_partners = failed_trackings.mapped('partner_id')
                failed_recipients = failed_partners.name_get()
                message['failed_recipients'] = failed_recipients
        return message_values

    @api.multi
    def _notify(self, force_send=False, send_after_commit=True,
                user_signature=True):
        """Force not adds followers to email (used when retry a message)"""
        self_sudo = self.sudo()
        hide_followers = self_sudo._context.get('default_hide_followers')
        if hide_followers:
            # HACK: Because Odoo uses subtype to found message followers
            # whe modify it to False to avoid include them.
            orig_subtype_id = self_sudo.subtype_id
            self_sudo.subtype_id = False
        res = super()._notify(force_send=force_send,
                              send_after_commit=send_after_commit,
                              user_signature=user_signature)
        if hide_followers:
            self_sudo.subtype_id = orig_subtype_id

        return res
