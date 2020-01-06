# Copyright 2017 Emanuel Cino - <ecino@compassion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, fields


class MailTrackingEvent(models.Model):
    _inherit = "mail.tracking.event"

    @api.model
    def process_sent(self, tracking_email, metadata):
        return self._process_status(
            tracking_email, metadata, 'sent', 'sent')

    def _process_status(self, tracking_email, metadata, event_type, state):
        switcher = {
            'processed': 'sent',
            'sent': 'sent',
            'delivered': 'received',
            'deferred': 'sent',
            'dropped': 'exception',
            'soft-bounced': 'exception',
            'bounce': 'exception',
            'opened': 'received',
            'spam': 'received',
            'unsub': 'received',
            'rejected': 'exception'
        }
        mail_state = switcher.get(state, 'exception')
        tracking_email.sudo().write({
            'state': state
        })
        tracking_email.mail_id.sudo().write({
            'state': mail_state
        })
        return self._process_data(tracking_email, metadata, event_type, state)

    def _process_bounce(self, tracking_email, metadata, event_type, state):
        tracking_email.sudo().write({
            'bounce_type': metadata.get('bounce_type', False),
            'bounce_description': metadata.get('bounce_description', False),
        })
        self._process_status(tracking_email, metadata, event_type, state)
        return self._process_data(tracking_email, metadata, event_type, state)
