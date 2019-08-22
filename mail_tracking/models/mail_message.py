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

    def _partner_tracking_status_human_get(self, status):
        statuses = {'waiting': _('Waiting'), 'error': _('Error'),
                    'sent': _('Sent'), 'delivered': _('Delivered'),
                    'opened': _('Opened'), 'unknown': _('Unknown')}
        return _("Status: %s") % statuses[status]

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
                partner_trackings.append({
                    'status': status,
                    'status_human':
                        self._partner_tracking_status_human_get(status),
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
            for partner in partners:
                # If there is partners not included, then status is 'unknown'
                # Because can be an Cc recipient
                isCc = False
                if partner.email in email_cc_list:
                    email_cc_list.discard(partner.email)
                    isCc = True
                partner_trackings.append({
                    'status': 'unknown',
                    'status_human':
                        self._partner_tracking_status_human_get('unknown'),
                    'tracking_id': False,
                    'recipient': partner.name,
                    'partner_id': partner.id,
                    'isCc': isCc,
                })
            for email in email_cc_list:
                # If there is Cc without partner
                partner_trackings.append({
                    'status': 'unknown',
                    'status_human':
                        self._partner_tracking_status_human_get('unknown'),
                    'tracking_id': False,
                    'recipient': email,
                    'partner_id': False,
                    'isCc': True,
                })
            res[message.id] = partner_trackings
        return res

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        res = super(MailMessage, self)._message_read_dict_postprocess(
            messages, message_tree)
        mail_message_ids = {m.get('id') for m in messages if m.get('id')}
        mail_messages = self.browse(mail_message_ids)
        partner_trackings = mail_messages.tracking_status()
        for message_dict in messages:
            mail_message_id = message_dict.get('id', False)
            if mail_message_id:
                message_dict['partner_trackings'] = \
                    partner_trackings[mail_message_id]
        return res
