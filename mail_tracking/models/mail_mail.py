# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from datetime import datetime
from email.utils import COMMASPACE

from openerp import models, api, fields


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.model
    def _tracking_email_prepare(self, mail, partner, email):
        ts = time.time()
        dt = datetime.utcfromtimestamp(ts)
        email_to_list = email.get('email_to', [])
        email_to = COMMASPACE.join(email_to_list)
        return {
            'name': email.get('subject', False),
            'timestamp': '%.6f' % ts,
            'time': fields.Datetime.to_string(dt),
            'mail_id': mail.id if mail else False,
            'mail_message_id': mail.mail_message_id.id if mail else False,
            'partner_id': partner.id if partner else False,
            'recipient': email_to,
            'sender': mail.email_from,
        }

    @api.model
    def send_get_email_dict(self, mail, partner=None):
        email = super(MailMail, self).send_get_email_dict(
            mail, partner=partner)
        m_tracking = self.env['mail.tracking.email']
        tracking_email = False
        if mail:
            vals = self._tracking_email_prepare(mail, partner, email)
            tracking_email = m_tracking.sudo().create(vals)
        if tracking_email:
            email = tracking_email.tracking_img_add(email)
        return email
