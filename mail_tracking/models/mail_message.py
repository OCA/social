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
            # Search all trackings for this message
            for tracking in trackings:
                status = self._partner_tracking_status_get(tracking)
                recipient = (
                    tracking.partner_id.name or tracking.recipient)
                partner_trackings.append((
                    status, tracking.id, recipient, tracking.partner_id.id))
                if tracking.partner_id:
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
                partner_trackings.append((
                    'unknown', False, partner.name, partner.id, partner.email))
            res[message.id] = partner_trackings
        return res

    @api.multi
    def _get_email_cc(self):
        """This method gets all Cc mails and the associated partner if exist.
            The result is a dictionary by 'message id' with a list of tuples
            (str:email_cc, list:[partner id, partner display_name] or False)
        """
        res = {}
        ResPartnerObj = self.env['res.partner']
        for message in self:
            email_cc_list = email_split(message.email_cc)
            email_cc_list_checked = []
            if any(email_cc_list):
                partners = ResPartnerObj.search([
                    ('email', 'in', email_cc_list)
                ])
                email_cc_list = set(email_cc_list)
                for partner in partners:
                    email_cc_list.discard(partner.email)
                    email_cc_list_checked.append(
                        (partner.email, [partner.id, partner.display_name]))
                for email in email_cc_list:
                    email_cc_list_checked.append((email, False))
            res.update({
                message.id: email_cc_list_checked
            })
        return res

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        res = super(MailMessage, self)._message_read_dict_postprocess(
            messages, message_tree)
        mail_message_ids = {m.get('id') for m in messages if m.get('id')}
        mail_messages = self.browse(mail_message_ids)
        partner_trackings = mail_messages.tracking_status()
        email_cc = mail_messages._get_email_cc()
        for message_dict in messages:
            mail_message_id = message_dict.get('id', False)
            if mail_message_id:
                message_dict.update({
                    'partner_trackings': partner_trackings[mail_message_id],
                    'email_cc': email_cc[mail_message_id],
                })
        return res
