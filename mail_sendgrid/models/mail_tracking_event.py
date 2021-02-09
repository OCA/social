# -*- coding: utf-8 -*-
# Copyright 2017 Emanuel Cino - <ecino@compassion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api


class MailTrackingEvent(models.Model):
    _inherit = "mail.tracking.event"

    @api.model
    def process_sent(self, tracking_email, metadata):
        return self._process_status(
            tracking_email, metadata, 'sent', 'sent')
