# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api
import logging
_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

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

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        res = super(MailMessage, self)._message_read_dict_postprocess(
            messages, message_tree)
        for message_dict in messages:
            mail_message_id = message_dict.get('id', False)
            if mail_message_id:
                partner_trackings = {}
                for partner in message_dict.get('partner_ids', []):
                    partner_id = partner[0]
                    tracking_email = self.env['mail.tracking.email'].search([
                        ('mail_message_id', '=', mail_message_id),
                        ('partner_id', '=', partner_id),
                    ], limit=1)
                    status = self._partner_tracking_status_get(tracking_email)
                    partner_trackings[str(partner_id)] = (
                        status, tracking_email.id)
            message_dict['partner_trackings'] = partner_trackings
        return res
