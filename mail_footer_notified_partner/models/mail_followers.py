# -*- coding: utf-8 -*-
# © 2016 ACSONE SA/NV <https://acsone.eu>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api
from odoo.tools.translate import _


class MailNotification(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _notify_send(self, body, subject, recipients, **mail_values):
        body += self.get_additional_footer(recipients)
        return super(MailNotification, self).\
            _notify_send(body, subject, recipients, **mail_values)

    @api.model
    def get_additional_footer(self, recipients):
        recipients_name = [
            recipient.name for recipient in recipients
        ]
        additional_footer = u'<br /><small>%s%s.</small><br />' % \
                            (_('Also notified: '),
                             ', '.join(recipients_name))
        return additional_footer
