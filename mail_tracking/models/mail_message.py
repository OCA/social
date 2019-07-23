# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, fields
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

    @api.model
    def get_failed_states(self):
        return {'error', 'rejected', 'spam', 'bounced', 'soft-bounced'}

    def _tracking_status_map_get(self):
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
        tracking_status_map = self._tracking_status_map_get()
        status = 'unknown'
        if tracking_email:
            tracking_email_status = str(tracking_email.state)
            status = tracking_status_map.get(tracking_email_status, 'unknown')
        return status

    def tracking_status(self):
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
                partner_trackings.append((
                    status, tracking.id, recipient, tracking.partner_id.id,
                    False))
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
            for partner in partners:
                # If there is partners not included, then status is 'unknown'
                # Because can be an Cc recipinet
                isCc = False
                if partner.email in email_cc_list:
                    email_cc_list.discard(partner.email)
                    isCc = True
                partner_trackings.append((
                    'unknown', False, partner.name, partner.id, isCc))
            for email in email_cc_list:
                # If there is Cc without partner
                partner_trackings.append((
                    'unknown', False, email, False, True))
            res[message.id] = partner_trackings
        return res

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        res = super(MailMessage, self)._message_read_dict_postprocess(
            messages, message_tree)
        mail_message_ids = {m.get('id') for m in messages if m.get('id')}
        mail_messages = self.browse(mail_message_ids)
        partner_trackings = mail_messages.tracking_status()
        failed_message = mail_messages._get_failed_message()
        for message_dict in messages:
            mail_message_id = message_dict.get('id', False)
            if mail_message_id:
                message_dict.update({
                    'partner_trackings': partner_trackings[mail_message_id],
                    'failed_message': failed_message[mail_message_id],
                })
                message_dict['partner_trackings'] = \
                    partner_trackings[mail_message_id]
        return res

    @api.model
    def _prepare_dict_failed_message(self, message):
        failed_trackings = message.mail_tracking_ids.filtered(
            lambda x: x.state in self.get_failed_states())
        failed_partners = failed_trackings.mapped('partner_id')
        failed_recipients = failed_partners.name_get()
        return {
            'id': message.id,
            'date': message.date,
            'author_id': message.author_id.name_get()[0],
            'body': message.body,
            'failed_recipients': failed_recipients,
        }

    @api.multi
    def get_failed_messages(self):
        return [self._prepare_dict_failed_message(msg) for msg in self]

    @api.multi
    def toggle_tracking_status(self):
        """Toggle message tracking action needed to ignore them in the tracking
           issues filter"""
        self.mail_tracking_needs_action = not self.mail_tracking_needs_action
        return self.mail_tracking_needs_action

    def _get_failed_message_domain(self):
        return [
            ('mail_tracking_ids.state', 'in', list(self.get_failed_states())),
            ('mail_tracking_needs_action', '=', True)
        ]

    @api.model
    def get_failed_count(self):
        """ Gets the number of failed messages """
        return self.search_count(self._get_failed_message_domain())

    @api.model
    def message_fetch(self, domain, limit=20):
        # HACK: Because can't modify the domain in discuss JS to search the
        # failed messages we force the change here to clean it of
        # not valid criterias
        if self.env.context.get('filter_failed_message'):
            domain = self._get_failed_message_domain()
        return super().message_fetch(domain, limit=limit)

    @api.multi
    def _notify(self, force_send=False, send_after_commit=True,
                user_signature=True):
        self_sudo = self.sudo()
        hide_followers = self_sudo._context.get('default_hide_followers',
                                                False)
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
